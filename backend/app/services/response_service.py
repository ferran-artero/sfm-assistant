import json
from pathlib import Path
from typing import Any
import logging

from app.services.llm_service import llm_service
from app.services.station_service import station_service
from app.services.hallucination_guard import hallucination_guard


PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "response_prompt.txt"
MAX_RESULTS_TO_MENTION = 3
logger = logging.getLogger("sfm.response")


class ResponseService:
    """
    Genera respostes finals per a l'usuari.

    Regla principal:
    - Les dades venen del backend.
    - Gemini només redacta.
    - Si Gemini falla o inventa hores, usam plantilla segura.
    """

    def __init__(self) -> None:
        self.stop_name_index = self._build_stop_name_index()

    def build_simple_response(
        self,
        intent_result: dict[str, Any],
    ) -> dict[str, Any]:
        intent = intent_result.get("intent")

        if intent == "greeting":
            return {
                "response": "Hola! Puc ajudar-te a consultar horaris de tren i metro de Mallorca.",
                "source": "template",
            }

        if intent == "thanks":
            return {
                "response": "De res! Si necessites consultar algun altre trajecte, no dubtis en dir-m'ho!",
                "source": "template",
            }

        if intent == "goodbye":
            return {
                "response": "Adéu! Bon viatge :)",
                "source": "template",
            }

        if intent == "empty":
            return {
                "response": "No he rebut cap missatge. Escriu-me una consulta sobre trens o metro de Mallorca.",
                "source": "template",
            }

        if intent == "out_of_domain":
            return {
                "response": (
                    "Ara mateix només puc ajudar-te amb consultes de tren i metro de Mallorca."
                ),
                "source": "template",
            }

        return {
            "response": "No he entès bé la consulta. Podries reformular-la?",
            "source": "template",
        }

    def build_clarification_response(
        self,
        conversation_result: dict[str, Any],
    ) -> dict[str, Any]:
        clarification_message = conversation_result.get("clarification_message")

        if clarification_message:
            return {
                "response": clarification_message,
                "source": "template",
            }

        return {
            "response": "Em falta informació per completar la consulta.",
            "source": "template",
        }

    def build_known_place_without_train_response(
        self,
        places: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not places:
            return {
                "response": "Desafortunadament, aquest lloc encara no disposa d'aturada de tren o metro...",
                "source": "template",
            }

        place = places[0]
        display_name = place.get("display_name") or place.get("id") or "aquest lloc"

        message = place.get("message")
        if message:
            return {
                "response": message,
                "source": "template",
            }

        return {
            "response": (
                f"{display_name} encara no disposa d'aturada de tren o metro."
            ),
            "source": "template",
        }

    def build_train_results_response(
        self,
        query: dict[str, Any],
        results: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Genera una resposta per resultats de tren/metro.

        Primer prova Gemini.
        Si Gemini falla, resposta amb plantilla.
        """
        if not results:
            return {
                "response": self._build_no_results_template(query),
                "source": "template",
            }

        safe_results = self._prepare_safe_results(results)
        safe_query = self._prepare_safe_query(query)
        safe_context = context or {}

        if llm_service.is_available():
            try:
                response = self._generate_train_response_with_gemini(
                    query=safe_query,
                    results=safe_results,
                    context=safe_context,
                )

                hallucination_guard.assert_response_is_safe(
                    response=response,
                    results=safe_results,
                    context={
                        "query": safe_query,
                        "source": "response_service",
                    },
                )

                return {
                    "response": response,
                    "source": "gemini",
                }

            except Exception as error:
                logger.exception(
                    "Gemini response failed. Using template_fallback. query=%s results_count=%s",
                    safe_query,
                    len(safe_results),
                )

                return {
                    "response": self._build_train_results_template(
                        query=safe_query,
                        results=safe_results,
                    ),
                    "source": "template_fallback",
                    "llm_error": str(error),
                }

        return {
            "response": self._build_train_results_template(
                query=safe_query,
                results=safe_results,
            ),
            "source": "template",
        }

    def _generate_train_response_with_gemini(
        self,
        query: dict[str, Any],
        results: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> str:
        if not PROMPT_FILE.exists():
            raise FileNotFoundError(f"No s'ha trobat el prompt: {PROMPT_FILE}")

        template = PROMPT_FILE.read_text(encoding="utf-8")

        prompt = (
            template
            .replace("{{query_json}}", json.dumps(query, ensure_ascii=False, indent=2))
            .replace("{{results_json}}", json.dumps(results, ensure_ascii=False, indent=2))
            .replace("{{context_json}}", json.dumps(context, ensure_ascii=False, indent=2))
        )

        raw_result = llm_service.generate_json(prompt)

        response = raw_result.get("response")

        if not response or not isinstance(response, str):
            raise ValueError("Gemini no ha retornat una resposta textual vàlida.")

        return response.strip()

    def _prepare_safe_query(
        self,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        origin_stop_id = query.get("origin_stop_id")
        destination_stop_id = query.get("destination_stop_id")

        return {
            "query_type": query.get("query_type"),
            "origin_stop_id": origin_stop_id,
            "origin_name": self._get_stop_display_name(origin_stop_id),
            "destination_stop_id": destination_stop_id,
            "destination_name": self._get_stop_display_name(destination_stop_id),
            "date": query.get("date"),
            "time": query.get("time"),
            "time_window": query.get("time_window"),
            "departure_after": query.get("departure_after"),
            "arrival_before": query.get("arrival_before"),
            "service_id": query.get("service_id"),
        }

    def _prepare_safe_results(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        safe_results = []

        for result in results[:MAX_RESULTS_TO_MENTION]:
            origin = result.get("origin", {})
            destination = result.get("destination", {})

            origin_stop_id = origin.get("stop_id")
            destination_stop_id = destination.get("stop_id")

            safe_results.append(
                {
                    "trip_id": result.get("trip_id"),
                    "route_id": result.get("route_id"),
                    "route_name": result.get("route_name"),
                    "service_id": result.get("service_id"),
                    "headsign": result.get("headsign"),
                    "bikes_allowed": result.get("bikes_allowed"),
                    "origin": {
                        "stop_id": origin_stop_id,
                        "display_name": self._get_stop_display_name(origin_stop_id),
                        "time": origin.get("time"),
                    },
                    "destination": {
                        "stop_id": destination_stop_id,
                        "display_name": self._get_stop_display_name(destination_stop_id),
                        "time": destination.get("time"),
                    },
                    "duration_minutes": result.get("duration_minutes"),
                }
            )

        return safe_results

    def _build_train_results_template(
        self,
        query: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> str:
        first_result = results[0]

        origin_name = first_result["origin"]["display_name"]
        destination_name = first_result["destination"]["display_name"]

        if len(results) == 1:
            return self._format_single_result(
                result=first_result,
                origin_name=origin_name,
                destination_name=destination_name,
            )

        lines = [
            (
                f"He trobat {len(results)} opcions de {origin_name} "
                f"a {destination_name}:"
            )
        ]

        for index, result in enumerate(results[:MAX_RESULTS_TO_MENTION], start=1):
            lines.append(
                (
                    f"{index}. Surt a les {result['origin']['time']} i arriba "
                    f"a les {result['destination']['time']} "
                    f"({result['route_id']}, {result['duration_minutes']} min)."
                )
            )

        return "\n".join(lines)

    def _format_single_result(
        self,
        result: dict[str, Any],
        origin_name: str,
        destination_name: str,
    ) -> str:
        return (
            f"La pròxima opció de {origin_name} a {destination_name} surt "
            f"a les {result['origin']['time']} i arriba a les "
            f"{result['destination']['time']} "
            f"({result['route_id']}, {result['duration_minutes']} min)."
        )

    def _build_no_results_template(
        self,
        query: dict[str, Any],
    ) -> str:
        origin_name = self._get_stop_display_name(query.get("origin_stop_id"))
        destination_name = self._get_stop_display_name(query.get("destination_stop_id"))

        if origin_name and destination_name:
            return (
                f"No he trobat cap opció directa de {origin_name} a {destination_name} "
                "amb els criteris indicats."
            )

        if origin_name:
            return (
                f"No he trobat cap sortida des de {origin_name} amb els criteris indicats."
            )

        if destination_name:
            return (
                f"No he trobat cap arribada a {destination_name} amb els criteris indicats."
            )

        return "No he trobat cap resultat amb els criteris indicats."


    def _build_stop_name_index(self) -> dict[str, str]:
        index = {}

        for station in station_service.stations:
            stop_id = station.get("stop_id")
            display_name = station.get("display_name")

            if stop_id and display_name:
                index[stop_id] = display_name

        return index

    def _get_stop_display_name(
        self,
        stop_id: str | None,
    ) -> str | None:
        if not stop_id:
            return None

        return self.stop_name_index.get(stop_id, stop_id)


response_service = ResponseService()