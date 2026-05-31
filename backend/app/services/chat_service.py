from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import logging

from app.models import ChatResponse
from app.services.conversation_service import conversation_service
from app.services.intent_service import intent_service
from app.services.response_service import response_service
from app.services.station_service import station_service
from app.services.train_service import (
    minutes_to_time,
    time_to_minutes,
    train_service,
)


TIME_WINDOWS = {
    "morning": ("06:00", "12:00"),
    "midday": ("12:00", "15:00"),
    "afternoon": ("15:00", "20:00"),
    "evening": ("20:00", "23:59"),
}

DEFAULT_LIMIT = 3
TIMEZONE = ZoneInfo("Europe/Madrid")
logger = logging.getLogger("sfm.chat")


class ChatService:
    """
    Orquestra el flux complet del chatbot.

    Responsabilitats:
    - rebre missatge
    - interpretar intenció
    - completar context conversacional
    - consultar horaris
    - generar resposta final
    - guardar context
    """

    def handle_chat(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> ChatResponse:
        context = conversation_service.get_or_create_context(conversation_id)
        active_conversation_id = context["conversation_id"]

        conversation_service.add_message(
            conversation_id=active_conversation_id,
            role="user",
            content=message,
        )

        intent_result = intent_service.analyze_message(message)
        intent = intent_result.get("intent")

        logger.info(
            "Intent result | conversation_id=%s | message=%s | intent=%s | source=%s | query=%s",
            active_conversation_id,
            message,
            intent,
            intent_result.get("source"),
            intent_result.get("query"),
        )

        known_place_guard = self._detect_known_places_without_train_with_rules(
            conversation_id=active_conversation_id,
            message=message,
            current_intent=intent,
        )

        if known_place_guard:
            intent_result = {
                **intent_result,
                "intent": "train_query",
                "confidence": 0.95,
                "query": known_place_guard.get("query"),
                "detected_locations": known_place_guard.get("detected_locations", []),
                "known_places_without_train": known_place_guard["known_places_without_train"],
                "source": "rules_place_guard",
                "reason": "S'ha detectat un lloc conegut sense tren amb regles deterministes.",
            }

            intent = "train_query"

        contextual_followup = self._try_build_contextual_followup_query(
            conversation_id=active_conversation_id,
            message=message,
            intent=intent,
        )

        if contextual_followup:
            intent_result = {
                "intent": "train_query",
                "confidence": 0.95,
                "message": message,
                "normalized_message": message.lower().strip(),
                "query": contextual_followup["query"],
                "detected_locations": [],
                "known_places_without_train": [],
                "source": contextual_followup["source"],
                "reason": contextual_followup["reason"],
            }

            intent = "train_query"

        # 1. Salutació, gràcies, adeu, fora de domini, empty...
        if intent != "train_query":
            response_data = response_service.build_simple_response(intent_result)
        
            return self._finalize_response(
                conversation_id=active_conversation_id,
                response_text=response_data["response"],
                intent_source=intent_result.get("source"),
                response_source=response_data.get("source"),
                debug={
                    "intent": intent,
                    "intent_confidence": intent_result.get("confidence"),
                    "reason": intent_result.get("reason"),
                },
            )

        # 2. Lloc conegut sense tren, com Vilafranca, Alcúdia, Llucmajor...
        known_places_without_train = intent_result.get("known_places_without_train", [])

        if known_places_without_train:
            response_data = response_service.build_known_place_without_train_response(
                places=known_places_without_train,
            )

            return self._finalize_response(
                conversation_id=active_conversation_id,
                response_text=response_data["response"],
                intent_source=intent_result.get("source"),
                response_source=response_data.get("source"),
                debug={
                    "intent": intent,
                    "intent_confidence": intent_result.get("confidence"),
                    "known_places_without_train": known_places_without_train,
                },
            )

        query = intent_result.get("query") or {}

        query = self._adapt_query_for_pending_completion(
            conversation_id=active_conversation_id,
            query=query,
        )

        query = self._merge_with_last_query_if_temporal_followup(
            conversation_id=active_conversation_id,
            query=query,
        )

        query = self._normalize_query_type_for_time_window(query)

        # 3. Consultes relatives: "un més tard", "un abans"...
        if query.get("query_type") in ["later", "earlier"]:
            return self._handle_relative_query(
                conversation_id=active_conversation_id,
                query_type=query["query_type"],
            )

        # 4. Completar consulta amb memòria conversacional
        conversation_result = conversation_service.merge_with_pending_query(
            conversation_id=active_conversation_id,
            new_query=query,
        )

        # 5. Si falten dades, demanam aclariment
        if not conversation_result["is_complete"]:
            response_data = response_service.build_clarification_response(
                conversation_result,
            )

            return self._finalize_response(
                conversation_id=active_conversation_id,
                response_text=response_data["response"],
                intent_source=intent_result.get("source"),
                response_source=response_data.get("source"),
                debug={
                    "intent": intent,
                    "intent_confidence": intent_result.get("confidence"),
                    "query": query,
                    "pending_query": conversation_result.get("query"),
                    "missing_fields": conversation_result.get("missing_fields"),
                },
            )

        # 6. Consulta completa
        completed_query = conversation_result["query"]

        results = self._search_results_for_query(completed_query)

        conversation_service.save_last_results(
            conversation_id=active_conversation_id,
            results=results,
        )

        response_data = response_service.build_train_results_response(
            query=completed_query,
            results=results,
            context={
                "intent_source": intent_result.get("source"),
                "intent_confidence": intent_result.get("confidence"),
            },
        )

        logger.info(
            "Response result | conversation_id=%s | response_source=%s | results_count=%s | llm_error=%s",
            active_conversation_id,
            response_data.get("source"),
            len(results),
            response_data.get("llm_error"),
        )

        # 7. Resposta final amb debug
        return self._finalize_response(
            conversation_id=active_conversation_id,
            response_text=response_data["response"],
            intent_source=intent_result.get("source"),
            response_source=response_data.get("source"),
            debug={
                "intent": intent,
                "intent_confidence": intent_result.get("confidence"),
                "query": completed_query,
                "results_count": len(results),
                "response_source": response_data.get("source"),
                "llm_error": response_data.get("llm_error"),
            },
        )

    def _detect_known_places_without_train_with_rules(
        self,
        conversation_id: str,
        message: str,
        current_intent: str | None,
    ) -> dict[str, Any] | None:
        """
        Detecta llocs coneguts sense tren amb regles deterministes.

        Això evita dependre només de Gemini en casos com:
        - "des de Vilafranca"
        - "vull anar a Vilafranca"
        - "de Vilafranca a Palma"

        Especialment important quan hi ha una pending_query oberta.
        """
        rules_result = intent_service.analyze_message_with_rules(message)
        known_places = rules_result.get("known_places_without_train", [])

        if not known_places:
            return None

        has_pending_query = conversation_service.get_pending_query(conversation_id) is not None

        if current_intent == "train_query" or has_pending_query or self._message_has_travel_context(message):
            return {
                "query": rules_result.get("query"),
                "detected_locations": rules_result.get("detected_locations", []),
                "known_places_without_train": known_places,
            }

        return None
    
    def _message_has_travel_context(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower().strip()

        travel_markers = [
            "tren",
            "trens",
            "metro",
            "horari",
            "horaris",
            "vull anar",
            "anar",
            "sortir",
            "arribar",
            "des de",
            "desde",
            "cap a",
            "fins a",
            "de ",
        ]

        return any(marker in normalized for marker in travel_markers)

    def _try_build_query_from_pending_followup(
        self,
        message: str,
        pending_query: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Intenta interpretar una resposta curta de l'usuari quan hi ha una consulta pendent.

        Exemple:
        pending_query = {"origin_stop_id": "inca", "destination_stop_id": None}
        message = "manacor"
        resultat = {"destination_stop_id": "manacor"}
        """
        missing_fields = conversation_service.get_missing_fields(pending_query)

        rules_result = intent_service.analyze_message_with_rules(message)
        detected_locations = rules_result.get("detected_locations", [])

        valid_stations = [
            location
            for location in detected_locations
            if location.get("type") == "station"
        ]

        if valid_stations:
            stop_id = valid_stations[0].get("id")

            if "destination_stop_id" in missing_fields:
                return {
                    "destination_stop_id": stop_id,
                }

            if "origin_stop_id" in missing_fields:
                return {
                    "origin_stop_id": stop_id,
                }

        validation = station_service.validate_station(message)

        if validation.get("status") == "valid_station":
            stop_id = validation.get("stop_id")

        if "time_context" in missing_fields:
            time_window = self._detect_time_window_from_followup(message)

            if time_window:
                return {
                    "time_window": time_window,
                }

        if "departure_after" in missing_fields:
            detected_time = self._detect_simple_time_from_followup(message)

            if detected_time:
                return {
                    "departure_after": detected_time,
                }

        if "arrival_before" in missing_fields:
            detected_time = self._detect_simple_time_from_followup(message)

            if detected_time:
                return {
                    "arrival_before": detected_time,
                }

        return None
    
    def _try_build_contextual_followup_query(
        self,
        conversation_id: str,
        message: str,
        intent: str | None,
    ) -> dict[str, Any] | None:
        """
        Gestiona respostes curtes que Gemini o les regles poden haver classificat
        com a no train_query, però que tenen sentit pel context de conversa.

        Casos:
        - pending_query: "A Palma", "Manacor", "dematí"
        - last_query: "i demà dematí?", "i avui capvespre?", "i a les 17?"
        """
        if intent == "train_query":
            return None

        pending_query = conversation_service.get_pending_query(conversation_id)

        if pending_query:
            pending_followup_query = self._try_build_query_from_pending_followup(
                message=message,
                pending_query=pending_query,
            )

            if pending_followup_query:
                return {
                    "query": pending_followup_query,
                    "source": "pending_context",
                    "reason": "Resposta curta usada per completar una consulta pendent.",
                }

        last_query = conversation_service.get_last_query(conversation_id)

        if last_query:
            temporal_followup_query = self._try_build_temporal_query_from_followup(
                message=message,
            )

            if temporal_followup_query:
                return {
                    "query": temporal_followup_query,
                    "source": "last_query_context",
                    "reason": "Seguiment temporal aplicat a la darrera consulta completa.",
                }

        return None
    
    def _try_build_temporal_query_from_followup(
        self,
        message: str,
    ) -> dict[str, Any] | None:
        """
        Detecta missatges curts que només canvien el context temporal:
        - "i demà dematí?"
        - "demà capvespre"
        - "avui vespre"
        - "a les 17"
        """
        date = self._detect_date_from_followup(message)
        time_window = self._detect_time_window_from_followup(message)
        detected_time = self._detect_simple_time_from_followup(message)

        has_temporal_info = any(
            [
                self._has_value(date),
                self._has_value(time_window),
                self._has_value(detected_time),
            ]
        )

        if not has_temporal_info:
            return None

        normalized = message.lower().strip()

        query_type = "next_departure"
        departure_after = None
        arrival_before = None
        time = None

        if time_window:
            query_type = "list_trains"

        elif detected_time and any(word in normalized for word in ["abans", "arribar abans"]):
            query_type = "arrival_before"
            arrival_before = detected_time

        elif detected_time and any(word in normalized for word in ["després", "despres", "a partir"]):
            query_type = "departure_after"
            departure_after = detected_time

        elif detected_time:
            query_type = "next_departure"
            time = detected_time

        return {
            "query_type": query_type,
            "origin_stop_id": None,
            "destination_stop_id": None,
            "date": date,
            "time": time,
            "time_window": time_window,
            "departure_after": departure_after,
            "arrival_before": arrival_before,
            "service_id": None,
        }

    def _detect_time_window_from_followup(
        self,
        message: str,
    ) -> str | None:
        normalized = message.lower().strip()

        if any(word in normalized for word in ["demati", "dematí", "mati", "matí"]):
            return "morning"

        if any(word in normalized for word in ["migdia", "mig dia", "mediodia", "mediodía"]):
            return "midday"

        if any(word in normalized for word in ["tarda", "horabaixa", "capvespre"]):
            return "afternoon"

        if any(word in normalized for word in ["vespre", "nit", "noche"]):
            return "evening"

        return None

    def _detect_date_from_followup(
        self,
        message: str,
    ) -> str | None:
        normalized = message.lower().strip()

        if any(word in normalized for word in ["avui", "hui"]):
            return "today"

        if any(word in normalized for word in ["demà", "dema"]):
            return "tomorrow"

        if any(word in normalized for word in ["dissabte", "sábado", "sabado"]):
            return "saturday"

        if any(word in normalized for word in ["diumenge", "domingo"]):
            return "sunday"

        if any(word in normalized for word in ["cap de setmana", "finde", "weekend"]):
            return "weekend"

        weekdays = {
            "dilluns": "monday",
            "dimarts": "tuesday",
            "dimecres": "wednesday",
            "dijous": "thursday",
            "divendres": "friday",
        }

        for word, value in weekdays.items():
            if word in normalized:
                return value

        return None

    def _detect_simple_time_from_followup(
        self,
        message: str,
    ) -> str | None:
        import re

        normalized = message.lower().strip()

        time_with_minutes = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", normalized)

        if time_with_minutes:
            hour = int(time_with_minutes.group(1))
            minute = int(time_with_minutes.group(2))
            return f"{hour:02d}:{minute:02d}"

        time_without_minutes = re.search(
            r"\b(?:a les|a|a las|les|las|abans de les|despres de les|després de les|a partir de les)\s+([0-2]?\d)\b",
            normalized,
        )

        if time_without_minutes:
            hour = int(time_without_minutes.group(1))

            if 0 <= hour <= 23:
                return f"{hour:02d}:00"

        return None

    def _merge_with_last_query_if_temporal_followup(
        self,
        conversation_id: str,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Si l'usuari fa un seguiment temporal del tipus:
        - "i demà dematí?"
        - "i avui capvespre?"
        - "i a les 17?"
        
        reutilitzam l'origen i la destinació de la darrera consulta completa.
        """
        last_query = conversation_service.get_last_query(conversation_id)

        if not last_query:
            return query

        has_origin_or_destination = any(
            [
                self._has_value(query.get("origin_stop_id")),
                self._has_value(query.get("destination_stop_id")),
            ]
        )

        has_temporal_info = any(
            [
                self._has_value(query.get("date")),
                self._has_value(query.get("time")),
                self._has_value(query.get("time_window")),
                self._has_value(query.get("departure_after")),
                self._has_value(query.get("arrival_before")),
            ]
        )

        if has_origin_or_destination or not has_temporal_info:
            return query

        merged_query = {
            **last_query,
            **{
                key: value
                for key, value in query.items()
                if self._has_value(value)
            },
        }

        if self._has_value(query.get("time_window")):
            merged_query["query_type"] = "list_trains"
            merged_query["time"] = None
            merged_query["departure_after"] = None
            merged_query["arrival_before"] = None

        elif self._has_value(query.get("departure_after")):
            merged_query["query_type"] = "departure_after"
            merged_query["time"] = None
            merged_query["time_window"] = None
            merged_query["arrival_before"] = None

        elif self._has_value(query.get("arrival_before")):
            merged_query["query_type"] = "arrival_before"
            merged_query["time"] = None
            merged_query["time_window"] = None
            merged_query["departure_after"] = None

        elif self._has_value(query.get("time")):
            merged_query["query_type"] = query.get("query_type") or "next_departure"
            merged_query["time_window"] = None
            merged_query["departure_after"] = None
            merged_query["arrival_before"] = None

        return merged_query

    def _has_value(
        self,
        value: Any,
    ) -> bool:
        return value is not None and value != "" and value != []

    def _handle_relative_query(
        self,
        conversation_id: str,
        query_type: str,
    ) -> ChatResponse:
        last_query = conversation_service.get_last_query(conversation_id)
        last_results = conversation_service.get_last_results(conversation_id)

        if not last_query or not last_results:
            return self._finalize_response(
                conversation_id=conversation_id,
                response_text=(
                    "Necessit una consulta anterior per poder cercar una opció "
                    "més tard o més prest."
                ),
            )

        if query_type == "later":
            last_departure = last_results[-1]["origin"]["time"]
            next_time = minutes_to_time(time_to_minutes(last_departure) + 1)

            new_query = {
                **last_query,
                "query_type": "next_departure",
                "time": next_time,
                "departure_after": None,
                "arrival_before": None,
            }

            results = self._search_results_for_query(new_query)

        else:
            first_departure = last_results[0]["origin"]["time"]

            new_query = {
                **last_query,
                "query_type": "list_trains",
                "time": None,
                "time_window": None,
                "departure_after": None,
                "arrival_before": None,
            }

            results = train_service.search_trains_in_window(
                origin_stop_id=last_query["origin_stop_id"],
                destination_stop_id=last_query["destination_stop_id"],
                start_time="00:00",
                end_time=first_departure,
                service_id=self._resolve_service_id(last_query),
            )[-DEFAULT_LIMIT:]

        conversation_service.save_last_results(
            conversation_id=conversation_id,
            results=results,
        )

        response_data = response_service.build_train_results_response(
            query=new_query,
            results=results,
            context={
                "relative_query_type": query_type,
            },
        )

        return self._finalize_response(
            conversation_id=conversation_id,
            response_text=response_data["response"],
            intent_source="gemini_or_rules",
            response_source=response_data.get("source"),
            debug={
                "relative_query_type": query_type,
                "query": new_query,
                "results_count": len(results),
                "llm_error": response_data.get("llm_error"),
            },
        )
    
    def _normalize_query_type_for_time_window(
        self,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Si hi ha una franja del dia, l'usuari espera una llista
        d'opcions dins aquella franja, independentment del query_type anterior.
        """
        if self._has_value(query.get("time_window")):
            return {
                **query,
                "query_type": "list_trains",
                "time": None,
                "departure_after": None,
                "arrival_before": None,
            }

        return query

    def _search_results_for_query(
        self,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        query_type = query.get("query_type", "next_departure")
        service_id = self._resolve_service_id(query)

        origin = query.get("origin_stop_id")
        destination = query.get("destination_stop_id")

        if query_type == "next_departure":
            after_time = self._resolve_time_value(query.get("time")) or self._current_time()
            return train_service.search_next_departure(
                origin_stop_id=origin,
                destination_stop_id=destination,
                after_time=after_time,
                service_id=service_id,
                limit=DEFAULT_LIMIT,
            )

        if query_type == "list_trains":
            start_time, end_time = self._resolve_time_window(query)
            return train_service.search_trains_in_window(
                origin_stop_id=origin,
                destination_stop_id=destination,
                start_time=start_time,
                end_time=end_time,
                service_id=service_id,
            )[:DEFAULT_LIMIT]

        if query_type == "departure_after":
            departure_after = query.get("departure_after") or query.get("time") or self._current_time()
            return train_service.search_departure_after(
                origin_stop_id=origin,
                destination_stop_id=destination,
                departure_time=departure_after,
                service_id=service_id,
                limit=DEFAULT_LIMIT,
            )

        if query_type == "arrival_before":
            arrival_before = query.get("arrival_before") or query.get("time")
            return train_service.search_arrival_before(
                origin_stop_id=origin,
                destination_stop_id=destination,
                arrival_time=arrival_before,
                service_id=service_id,
                limit=DEFAULT_LIMIT,
            )

        if query_type == "departures_from_station":
            start_time, end_time = self._resolve_time_window(query)
            return train_service.search_departures_from_station(
                origin_stop_id=origin,
                start_time=start_time,
                end_time=end_time,
                service_id=service_id,
                limit=DEFAULT_LIMIT,
            )

        if query_type == "arrivals_to_station":
            start_time, end_time = self._resolve_time_window(query)
            return train_service.search_arrivals_to_station(
                destination_stop_id=destination,
                start_time=start_time,
                end_time=end_time,
                service_id=service_id,
                limit=DEFAULT_LIMIT,
            )

        return []

    def _adapt_query_for_pending_completion(
        self,
        conversation_id: str,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Si hi ha una consulta pendent i el nou missatge només completa
        origen o destinació, evitam que Gemini canviï query_type, time,
        time_window o altres camps de la consulta original.
        """
        pending_query = conversation_service.get_pending_query(conversation_id)

        if not pending_query:
            return query

        missing_fields = conversation_service.get_missing_fields(pending_query)

        has_temporal_update = any(
            [
                self._has_value(query.get("date")),
                self._has_value(query.get("time")),
                self._has_value(query.get("time_window")),
                self._has_value(query.get("departure_after")),
                self._has_value(query.get("arrival_before")),
            ]
        )

        completed_fields = {}

        if (
            "origin_stop_id" in missing_fields
            and self._has_value(query.get("origin_stop_id"))
        ):
            completed_fields["origin_stop_id"] = query["origin_stop_id"]

        if (
            "destination_stop_id" in missing_fields
            and self._has_value(query.get("destination_stop_id"))
        ):
            completed_fields["destination_stop_id"] = query["destination_stop_id"]

        if completed_fields and not has_temporal_update:
            return completed_fields

        return query

    def _resolve_time_window(
        self,
        query: dict[str, Any],
    ) -> tuple[str, str]:
        time_window = query.get("time_window")

        if time_window in TIME_WINDOWS:
            return TIME_WINDOWS[time_window]

        if query.get("time") == "now":
            start = self._current_time()
            end = minutes_to_time(time_to_minutes(start) + 120)
            return start, end

        if query.get("time"):
            start = query["time"]
            end = minutes_to_time(time_to_minutes(start) + 120)
            return start, end

        if query.get("departure_after"):
            return query["departure_after"], "23:59"

        if query.get("arrival_before"):
            return "00:00", query["arrival_before"]

        return "00:00", "23:59"

    def _resolve_time_value(
        self,
        value: str | None,
    ) -> str | None:
        if not value:
            return None

        if value == "now":
            return self._current_time()

        return value

    def _current_time(self) -> str:
        return datetime.now(TIMEZONE).strftime("%H:%M")

    def _resolve_service_id(
        self,
        query: dict[str, Any],
    ) -> str | None:
        if query.get("service_id"):
            return query["service_id"]

        mode = self._guess_mode(query)
        date_value = query.get("date") or "today"

        if mode == "metro":
            if self._date_is_sunday_or_holiday_without_metro(date_value):
                return "metro_no_service"

            if self._date_is_saturday_or_weekend(date_value):
                return "metro_saturday"

            return "metro_weekday"

        if self._date_is_saturday_or_weekend(date_value):
            return "train_weekend_holiday"

        return "train_weekday"

    def _guess_mode(
        self,
        query: dict[str, Any],
    ) -> str:
        origin = query.get("origin_stop_id")
        destination = query.get("destination_stop_id")

        origin_modes = self._get_station_modes(origin)
        destination_modes = self._get_station_modes(destination)

        if origin_modes == {"metro"} or destination_modes == {"metro"}:
            return "metro"

        return "train"

    def _get_station_modes(
        self,
        stop_id: str | None,
    ) -> set[str]:
        if not stop_id:
            return set()

        for station in station_service.stations:
            if station.get("stop_id") == stop_id:
                return set(station.get("modes", []))

        return set()

    def _date_is_saturday_or_weekend(
        self,
        date_value: str | None,
    ) -> bool:
        if date_value in ["saturday", "sunday", "weekend"]:
            return True

        if date_value == "today":
            return datetime.now(TIMEZONE).weekday() >= 5

        if date_value == "tomorrow":
            return (datetime.now(TIMEZONE) + timedelta(days=1)).weekday() >= 5

        return False

    def _date_is_sunday_or_holiday_without_metro(
        self,
        date_value: str | None,
    ) -> bool:
        if date_value in ["sunday", "weekend"]:
            return True

        if date_value == "today":
            return datetime.now(TIMEZONE).weekday() == 6

        if date_value == "tomorrow":
            return (datetime.now(TIMEZONE) + timedelta(days=1)).weekday() == 6

        return False

    def _finalize_response(
        self,
        conversation_id: str,
        response_text: str,
        intent_source: str | None = None,
        response_source: str | None = None,
        debug: dict[str, Any] | None = None,
    ) -> ChatResponse:
        conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            response=response_text,
            intent_source=intent_source,
            response_source=response_source,
            debug=debug,
        )


chat_service = ChatService()