from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.station_service import station_service

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_value(value: Any) -> bool:
    return value is not None and value != "" and value != []


class ConversationService:
    """
    Memòria temporal en RAM per mantenir context de conversa.

    Per una demo és suficient:
    - es guarda mentre el servidor està encès
    - es perd quan reiniciam uvicorn
    """

    def __init__(self) -> None:
        self.memory: dict[str, dict[str, Any]] = {}

    def create_conversation_id(self) -> str:
        return str(uuid4())

    def get_or_create_context(
        self,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        if not conversation_id:
            conversation_id = self.create_conversation_id()

        if conversation_id not in self.memory:
            self.memory[conversation_id] = {
                "conversation_id": conversation_id,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "messages": [],
                "last_query": None,
                "last_results": None,
                "pending_query": None,
            }

        return self.memory[conversation_id]

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        context = self.get_or_create_context(conversation_id)

        context["messages"].append(
            {
                "role": role,
                "content": content,
                "timestamp": now_iso(),
            }
        )

        context["updated_at"] = now_iso()

    def merge_with_pending_query(
        self,
        conversation_id: str | None,
        new_query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Combina una consulta nova amb una consulta pendent anterior.

        Exemple:
        1) Usuari: "Vull sortir d'Inca"
        pending_query = {"origin_stop_id": "inca"}

        2) Usuari: "A Palma"
        new_query = {"destination_stop_id": "palma"}

        resultat = {"origin_stop_id": "inca", "destination_stop_id": "palma"}
        """
        context = self.get_or_create_context(conversation_id)
        pending_query = context.get("pending_query")

        if pending_query:
            merged_query = deepcopy(pending_query)
            completed_from_pending = True
        else:
            merged_query = {}
            completed_from_pending = False

        for key, value in new_query.items():
            if has_value(value):
                merged_query[key] = value

        merged_query = self._ensure_query_defaults(merged_query)
        merged_query = self._apply_defaults_for_query_type(merged_query)

        missing_fields = self.get_missing_fields(merged_query)
        is_complete = len(missing_fields) == 0

        if is_complete:
            context["last_query"] = merged_query
            context["pending_query"] = None
        else:
            context["pending_query"] = merged_query

        context["updated_at"] = now_iso()

        return {
            "conversation_id": context["conversation_id"],
            "query": merged_query,
            "missing_fields": missing_fields,
            "is_complete": is_complete,
            "completed_from_pending": completed_from_pending,
            "clarification_message": self.build_clarification_message(
                missing_fields=missing_fields,
                train_query=merged_query,
            ),
        }

    def get_missing_fields(
        self,
        train_query: dict[str, Any],
    ) -> list[str]:
        """
        Decideix quins camps falten segons el tipus de consulta.

        No totes les consultes necessiten origen + destinació.
        """
        query_type = train_query.get("query_type", "next_departure")

        missing_fields: list[str] = []

        if query_type == "next_departure":
            self._require_origin(train_query, missing_fields)
            self._require_destination(train_query, missing_fields)

        elif query_type == "list_trains":
            self._require_origin(train_query, missing_fields)
            self._require_destination(train_query, missing_fields)
            self._require_time_context(train_query, missing_fields)

        elif query_type == "departure_after":
            self._require_origin(train_query, missing_fields)
            self._require_destination(train_query, missing_fields)
            if not has_value(train_query.get("departure_after")):
                missing_fields.append("departure_after")

        elif query_type == "arrival_before":
            self._require_origin(train_query, missing_fields)
            self._require_destination(train_query, missing_fields)
            if not has_value(train_query.get("arrival_before")):
                missing_fields.append("arrival_before")

        elif query_type == "departures_from_station":
            self._require_origin(train_query, missing_fields)
            self._require_time_context(train_query, missing_fields)

        elif query_type == "arrivals_to_station":
            self._require_destination(train_query, missing_fields)
            self._require_time_context(train_query, missing_fields)

        elif query_type in ["later", "earlier"]:
            # Aquests query_types necessitaran last_query/last_results més endavant.
            # De moment no exigim camps nous aquí.
            pass

        else:
            # Fallback segur: si no coneixem el tipus, demanam origen i destinació.
            self._require_origin(train_query, missing_fields)
            self._require_destination(train_query, missing_fields)

        return missing_fields

    def save_last_results(
        self,
        conversation_id: str,
        results: list[dict[str, Any]],
    ) -> None:
        context = self.get_or_create_context(conversation_id)
        context["last_results"] = results
        context["updated_at"] = now_iso()

    def get_last_query(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        context = self.get_or_create_context(conversation_id)
        return context.get("last_query")

    def get_last_results(
        self,
        conversation_id: str,
    ) -> list[dict[str, Any]] | None:
        context = self.get_or_create_context(conversation_id)
        return context.get("last_results")

    def get_pending_query(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        context = self.get_or_create_context(conversation_id)
        return context.get("pending_query")

    def reset_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        if conversation_id in self.memory:
            del self.memory[conversation_id]
            return True

        return False

    def get_public_context(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        context = self.get_or_create_context(conversation_id)

        return {
            "conversation_id": context["conversation_id"],
            "created_at": context["created_at"],
            "updated_at": context["updated_at"],
            "last_query": context["last_query"],
            "last_results": context["last_results"],
            "pending_query": context["pending_query"],
            "messages_count": len(context["messages"]),
        }

    def _get_stop_display_name(
        self,
        stop_id: str | None,
    ) -> str | None:
        if not stop_id:
            return None

        for station in station_service.stations:
            if station.get("stop_id") == stop_id:
                return station.get("display_name") or station.get("official_name") or stop_id

        return stop_id

    def build_clarification_message(
        self,
        missing_fields: list[str],
        train_query: dict[str, Any],
    ) -> str | None:
        if not missing_fields:
            return None

        query_type = train_query.get("query_type", "next_departure")

        origin_stop_id = train_query.get("origin_stop_id")
        destination_stop_id = train_query.get("destination_stop_id")

        origin = self._get_stop_display_name(origin_stop_id)
        destination = self._get_stop_display_name(destination_stop_id)

        missing_origin = "origin_stop_id" in missing_fields
        missing_destination = "destination_stop_id" in missing_fields
        missing_time_context = "time_context" in missing_fields
        missing_departure_after = "departure_after" in missing_fields
        missing_arrival_before = "arrival_before" in missing_fields

        if missing_origin and missing_destination:
            return "Des de quina estació vols sortir i cap a quina estació vols anar?"

        if missing_origin:
            if destination:
                return f"Des de quina estació vols sortir per anar a {destination}?"
            return "Des de quina estació vols sortir?"

        if missing_destination:
            if origin:
                return f"Cap a quina estació vols anar des de {origin}?"
            return "Cap a quina estació vols anar?"

        if missing_departure_after:
            return "A partir de quina hora vols sortir?"

        if missing_arrival_before:
            return "Abans de quina hora vols arribar?"

        if missing_time_context:
            if query_type == "departures_from_station" and origin:
                return f"Per quin moment del dia vols veure sortides des de {origin}?"

            if query_type == "arrivals_to_station" and destination:
                return f"Per quin moment del dia vols veure arribades a {destination}?"

            if origin and destination:
                return (
                    f"Per quin moment del dia vols cercar trens de {origin} "
                    f"a {destination}? Per exemple: dematí, migdia, capvespre o vespre."
                )

            return "Per quin moment del dia vols consultar els horaris?"

        return "Em falta informació per completar la consulta."

    def _ensure_query_defaults(
        self,
        train_query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Garanteix que totes les consultes tenguin la mateixa forma.
        """
        return {
            "query_type": train_query.get("query_type", "next_departure"),
            "origin_stop_id": train_query.get("origin_stop_id"),
            "destination_stop_id": train_query.get("destination_stop_id"),
            "date": train_query.get("date"),
            "time": train_query.get("time"),
            "time_window": train_query.get("time_window"),
            "departure_after": train_query.get("departure_after"),
            "arrival_before": train_query.get("arrival_before"),
            "service_id": train_query.get("service_id"),
        }

    def _apply_defaults_for_query_type(
        self,
        train_query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Aplica valors per defecte quan té sentit.

        Per defecte:
        - si l'usuari no indica cap dia, assumim today
        - si demana la pròxima sortida i no indica hora, assumim now
        """
        query_type = train_query.get("query_type")

        if not has_value(train_query.get("date")):
            train_query["date"] = "today"

        if query_type == "next_departure":
            if not has_value(train_query.get("time")):
                train_query["time"] = "now"

        return train_query

    def _has_time_context(
        self,
        train_query: dict[str, Any],
    ) -> bool:
        """
        Consideram que hi ha context temporal si tenim qualsevol d'aquests camps.
        """
        return any(
            [
                has_value(train_query.get("time")),
                has_value(train_query.get("time_window")),
                has_value(train_query.get("departure_after")),
                has_value(train_query.get("arrival_before")),
            ]
        )

    def _require_origin(
        self,
        train_query: dict[str, Any],
        missing_fields: list[str],
    ) -> None:
        if not has_value(train_query.get("origin_stop_id")):
            missing_fields.append("origin_stop_id")

    def _require_destination(
        self,
        train_query: dict[str, Any],
        missing_fields: list[str],
    ) -> None:
        if not has_value(train_query.get("destination_stop_id")):
            missing_fields.append("destination_stop_id")

    def _require_time_context(
        self,
        train_query: dict[str, Any],
        missing_fields: list[str],
    ) -> None:
        if not self._has_time_context(train_query):
            missing_fields.append("time_context")


conversation_service = ConversationService()