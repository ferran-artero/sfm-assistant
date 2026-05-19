import re
from typing import Any
import json
from pathlib import Path

from app.services.llm_service import llm_service
from app.services.station_service import normalize_text, station_service


PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "intent_prompt.txt"

ALLOWED_INTENTS = {
    "greeting",
    "thanks",
    "goodbye",
    "train_query",
    "out_of_domain",
    "empty",
}

ALLOWED_QUERY_TYPES = {
    "next_departure",
    "list_trains",
    "departure_after",
    "arrival_before",
    "departures_from_station",
    "arrivals_to_station",
    "later",
    "earlier",
}

ALLOWED_DATES = {
    "today",
    "tomorrow",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "weekend",
    None,
}

ALLOWED_TIME_WINDOWS = {
    "morning",
    "midday",
    "afternoon",
    "evening",
    None,
}

GREETING_WORDS = [
    "hola",
    "bones",
    "bon dia",
    "bona tarda",
    "bon vespre",
    "hey",
    "ei",
]

THANKS_WORDS = [
    "gracies",
    "gracis",
    "merci",
    "moltes gracies",
    "perfecte gracies",
]

GOODBYE_WORDS = [
    "adeu",
    "adios",
    "fins aviat",
    "fins despres",
    "fins després",
    "bye",
]

TRAIN_KEYWORDS = [
    "tren",
    "trens",
    "metro",
    "horari",
    "horaris",
    "sortida",
    "sortides",
    "surt",
    "surten",
    "arriba",
    "arriben",
    "anar",
    "vull anar",
    "viatge",
    "trajecte",
    "linia",
    "línia",
]

OUT_OF_DOMAIN_KEYWORDS = [
    "temps",
    "meteo",
    "meteorologia",
    "pizza",
    "restaurant",
    "hotel",
    "vol",
    "avio",
    "avió",
    "cotxe",
    "bus",
    "autobus",
    "autobús",
]

TIME_WINDOWS = {
    "morning": [
        "demati",
        "dematí",
        "mati",
        "matí",
        "pel mati",
        "pel matí",
        "de mati",
        "de matí",
        "manana",
        "mañana",
    ],
    "midday": [
        "migdia",
        "mig dia",
        "mediodia",
        "mediodía",
    ],
    "afternoon": [
        "tarda",
        "horabaixa",
        "capvespre",
        "per la tarda",
        "per s horabaixa",
        "per l horabaixa",
    ],
    "evening": [
        "vespre",
        "nit",
        "per la nit",
        "per es vespre",
    ],
}


class IntentService:
    def analyze_message(self, message: str) -> dict[str, Any]:
        """
        Primer intenta interpretar amb Gemini.
        Si Gemini falla, usa el parser de regles de la Fase 6.
        """
        if llm_service.is_available():
            try:
                result = self._analyze_message_with_gemini(message)
                result["source"] = "gemini"
                return result
            except Exception as error:
                fallback = self.analyze_message_with_rules(message)
                fallback["source"] = "rules_fallback"
                fallback["llm_error"] = str(error)
                return fallback

        fallback = self.analyze_message_with_rules(message)
        fallback["source"] = "rules"
        return fallback
        
    def analyze_message_with_rules(self, message: str) -> dict[str, Any]:
        normalized = normalize_text(message)

        if not normalized:
            return {
                "intent": "empty",
                "confidence": 1.0,
                "message": message,
                "normalized_message": normalized,
                "query": None,
            }

        detected_locations = self._extract_locations(normalized)
        is_train_related = self._is_train_related(normalized, detected_locations)

        if is_train_related:
            return self._build_train_intent(
                original_message=message,
                normalized_message=normalized,
                detected_locations=detected_locations,
            )

        if self._contains_any(normalized, GREETING_WORDS):
            return {
                "intent": "greeting",
                "confidence": 0.95,
                "message": message,
                "normalized_message": normalized,
                "query": None,
            }

        if self._contains_any(normalized, THANKS_WORDS):
            return {
                "intent": "thanks",
                "confidence": 0.95,
                "message": message,
                "normalized_message": normalized,
                "query": None,
            }

        if self._contains_any(normalized, GOODBYE_WORDS):
            return {
                "intent": "goodbye",
                "confidence": 0.95,
                "message": message,
                "normalized_message": normalized,
                "query": None,
            }

        return {
            "intent": "out_of_domain",
            "confidence": 0.8,
            "message": message,
            "normalized_message": normalized,
            "query": None,
            "reason": "No sembla una consulta sobre trens o metro.",
        }

    def _build_train_intent(
        self,
        original_message: str,
        normalized_message: str,
        detected_locations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query_type = self._detect_query_type(normalized_message)
        date = self._detect_date(normalized_message)
        time_window = self._detect_time_window(normalized_message)
        detected_time = self._detect_time(normalized_message)

        origin_stop_id, destination_stop_id = self._extract_origin_destination(
            normalized_message=normalized_message,
            detected_locations=detected_locations,
            query_type=query_type,
        )

        departure_after = None
        arrival_before = None
        time = None

        if query_type == "departure_after":
            departure_after = detected_time
        elif query_type == "arrival_before":
            arrival_before = detected_time
        else:
            time = detected_time

        known_places_without_train = [
            location
            for location in detected_locations
            if location["type"] == "place_without_train"
        ]

        return {
            "intent": "train_query",
            "confidence": 0.85,
            "message": original_message,
            "normalized_message": normalized_message,
            "query": {
                "query_type": query_type,
                "origin_stop_id": origin_stop_id,
                "destination_stop_id": destination_stop_id,
                "date": date,
                "time": time,
                "time_window": time_window,
                "departure_after": departure_after,
                "arrival_before": arrival_before,
                "service_id": None,
            },
            "detected_locations": detected_locations,
            "known_places_without_train": known_places_without_train,
        }

    def _analyze_message_with_gemini(self, message: str) -> dict[str, Any]:
        prompt = self._build_intent_prompt(message)
        raw_result = llm_service.generate_json(prompt)

        return self._normalize_llm_result(
            original_message=message,
            raw_result=raw_result,
        )

    def _build_intent_prompt(self, message: str) -> str:
        if not PROMPT_FILE.exists():
            raise FileNotFoundError(f"No s'ha trobat el prompt: {PROMPT_FILE}")

        template = PROMPT_FILE.read_text(encoding="utf-8")

        station_catalog = self._build_catalog(
            items=station_service.stations,
            id_field="stop_id",
        )

        places_without_train_catalog = self._build_catalog(
            items=station_service.places_without_train,
            id_field="place_id",
        )

        return (
            template
            .replace("{{message}}", message)
            .replace("{{station_catalog}}", json.dumps(station_catalog, ensure_ascii=False))
            .replace("{{places_without_train_catalog}}", json.dumps(places_without_train_catalog, ensure_ascii=False))
        )

    def _build_catalog(
        self,
        items: list[dict[str, Any]],
        id_field: str,
    ) -> list[dict[str, Any]]:
        catalog = []

        for item in items:
            catalog.append(
                {
                    "id": item.get(id_field),
                    "name": item.get("display_name"),
                    "aliases": item.get("aliases", [])[:8],
                }
            )

        return catalog

    def _normalize_llm_result(
        self,
        original_message: str,
        raw_result: dict[str, Any],
    ) -> dict[str, Any]:
        intent = raw_result.get("intent", "out_of_domain")

        if intent not in ALLOWED_INTENTS:
            raise ValueError(f"Intent no permès: {intent}")

        confidence = raw_result.get("confidence", 0.7)

        if intent != "train_query":
            return {
                "intent": intent,
                "confidence": confidence,
                "message": original_message,
                "normalized_message": normalize_text(original_message),
                "query": None,
                "reason": raw_result.get("reason", ""),
            }

        raw_query = raw_result.get("query", {})

        if not isinstance(raw_query, dict):
            raise ValueError("El camp query no és un objecte JSON.")

        query_type = raw_query.get("query_type", "next_departure")

        if query_type not in ALLOWED_QUERY_TYPES:
            query_type = "next_departure"

        date = raw_query.get("date")
        if date not in ALLOWED_DATES:
            date = None

        time_window = raw_query.get("time_window")
        if time_window not in ALLOWED_TIME_WINDOWS:
            time_window = None

        origin_text = raw_query.get("origin_text") or raw_query.get("origin")
        destination_text = raw_query.get("destination_text") or raw_query.get("destination")

        origin_info = self._resolve_location_text(origin_text)
        destination_info = self._resolve_location_text(destination_text)

        origin_stop_id = None
        destination_stop_id = None
        detected_locations = []
        known_places_without_train = []

        if origin_info:
            detected_locations.append(origin_info)

            if origin_info["type"] == "station":
                origin_stop_id = origin_info["id"]

            if origin_info["type"] == "place_without_train":
                known_places_without_train.append(origin_info)

        if destination_info:
            detected_locations.append(destination_info)

            if destination_info["type"] == "station":
                destination_stop_id = destination_info["id"]

            if destination_info["type"] == "place_without_train":
                known_places_without_train.append(destination_info)

        return {
            "intent": "train_query",
            "confidence": confidence,
            "message": original_message,
            "normalized_message": normalize_text(original_message),
            "query": {
                "query_type": query_type,
                "origin_stop_id": origin_stop_id,
                "destination_stop_id": destination_stop_id,
                "date": date,
                "time": raw_query.get("time"),
                "time_window": time_window,
                "departure_after": raw_query.get("departure_after"),
                "arrival_before": raw_query.get("arrival_before"),
                "service_id": raw_query.get("service_id"),
            },
            "detected_locations": detected_locations,
            "known_places_without_train": known_places_without_train,
            "reason": raw_result.get("reason", ""),
        }

    def _resolve_location_text(
        self,
        location_text: str | None,
    ) -> dict[str, Any] | None:
        if not location_text:
            return None

        validation = station_service.validate_station(location_text)
        status = validation.get("status")

        if status == "valid_station":
            return {
                "type": "station",
                "id": validation.get("stop_id"),
                "display_name": validation.get("display_name"),
                "input": location_text,
                "status": status,
            }

        if status == "known_place_without_train":
            return {
                "type": "place_without_train",
                "id": validation.get("place_id"),
                "display_name": validation.get("display_name"),
                "input": location_text,
                "status": status,
                "message": validation.get("message"),
            }

        if status == "typo_suggestion":
            suggestion = validation.get("suggestion", {})

            if suggestion.get("type") == "station":
                return {
                    "type": "station",
                    "id": suggestion.get("stop_id"),
                    "display_name": suggestion.get("display_name"),
                    "input": location_text,
                    "status": status,
                }

            if suggestion.get("type") == "place_without_train":
                return {
                    "type": "place_without_train",
                    "id": suggestion.get("place_id"),
                    "display_name": suggestion.get("display_name"),
                    "input": location_text,
                    "status": status,
                }

        return {
            "type": "unknown",
            "id": None,
            "display_name": location_text,
            "input": location_text,
            "status": status,
        }

    def _detect_query_type(self, normalized_message: str) -> str:
        if self._contains_any(
            normalized_message,
            [
                "abans de",
                "abans que",
                "arribar abans",
                "arriben abans",
                "arribi abans",
            ],
        ):
            return "arrival_before"

        if self._contains_any(
            normalized_message,
            [
                "despres de",
                "després de",
                "a partir de",
                "sortir despres",
                "sortir després",
                "surten despres",
                "surten després",
            ],
        ):
            return "departure_after"

        if self._contains_any(
            normalized_message,
            [
                "arribades",
                "arriben a",
                "arriba a",
                "que arriben",
            ],
        ):
            return "arrivals_to_station"

        if self._contains_any(
            normalized_message,
            [
                "sortides",
                "surten de",
                "surt de",
                "que surten",
            ],
        ):
            return "departures_from_station"

        if self._contains_any(
            normalized_message,
            [
                "quins trens",
                "quins metros",
                "horaris",
                "llistat",
                "tots els trens",
                "trens hi ha",
            ],
        ):
            return "list_trains"

        if self._contains_any(
            normalized_message,
            [
                "proxim",
                "pròxim",
                "proxima",
                "pròxima",
                "seguent",
                "següent",
            ],
        ):
            return "next_departure"

        return "next_departure"

    def _detect_date(self, normalized_message: str) -> str | None:
        if self._contains_any(normalized_message, ["avui", "hui"]):
            return "today"

        if self._contains_any(normalized_message, ["dema", "demà", "demain"]):
            return "tomorrow"

        if self._contains_any(normalized_message, ["dissabte", "sabado", "sábado"]):
            return "saturday"

        if self._contains_any(normalized_message, ["diumenge", "domingo"]):
            return "sunday"

        if self._contains_any(
            normalized_message,
            ["cap de setmana", "finde", "weekend"],
        ):
            return "weekend"

        weekdays = {
            "dilluns": "monday",
            "dimarts": "tuesday",
            "dimecres": "wednesday",
            "dijous": "thursday",
            "divendres": "friday",
        }

        for word, value in weekdays.items():
            if word in normalized_message:
                return value

        return None

    def _detect_time_window(self, normalized_message: str) -> str | None:
        for time_window, words in TIME_WINDOWS.items():
            if self._contains_any(normalized_message, words):
                return time_window

        return None

    def _detect_time(self, normalized_message: str) -> str | None:
        """
        Detecta hores simples:
        - 09:30
        - 9:30
        - a les 9
        - abans de les 9
        - després de les 17
        """
        time_with_minutes = re.search(
            r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b",
            normalized_message,
        )

        if time_with_minutes:
            hour = int(time_with_minutes.group(1))
            minute = int(time_with_minutes.group(2))
            return f"{hour:02d}:{minute:02d}"

        time_without_minutes = re.search(
            r"\b(?:a les|a las|les|las|abans de les|despres de les|després de les|a partir de les)\s+([0-2]?\d)\b",
            normalized_message,
        )

        if time_without_minutes:
            hour = int(time_without_minutes.group(1))

            if 0 <= hour <= 23:
                return f"{hour:02d}:00"

        return None

    def _extract_origin_destination(
        self,
        normalized_message: str,
        detected_locations: list[dict[str, Any]],
        query_type: str,
    ) -> tuple[str | None, str | None]:
        valid_stations = [
            location
            for location in detected_locations
            if location["type"] == "station"
        ]

        origin_stop_id = None
        destination_stop_id = None

        for location in valid_stations:
            if self._has_origin_marker_before(normalized_message, location):
                origin_stop_id = location["id"]

            if self._has_destination_marker_before(normalized_message, location):
                destination_stop_id = location["id"]

        if query_type == "departures_from_station":
            if not origin_stop_id and valid_stations:
                origin_stop_id = valid_stations[0]["id"]

        if query_type == "arrivals_to_station":
            if not destination_stop_id and valid_stations:
                destination_stop_id = valid_stations[-1]["id"]

        if len(valid_stations) >= 2:
            if not origin_stop_id:
                origin_stop_id = valid_stations[0]["id"]

            if not destination_stop_id:
                destination_stop_id = valid_stations[1]["id"]

        if len(valid_stations) == 1:
            location = valid_stations[0]

            if not origin_stop_id and not destination_stop_id:
                if normalized_message.startswith(("a ", "cap a ", "fins a ", "hasta ")):
                    destination_stop_id = location["id"]
                elif normalized_message.startswith(("de ", "des de ", "desde ", "d ")):
                    origin_stop_id = location["id"]
                elif query_type == "departures_from_station":
                    origin_stop_id = location["id"]
                elif query_type == "arrivals_to_station":
                    destination_stop_id = location["id"]
                else:
                    destination_stop_id = location["id"]

        return origin_stop_id, destination_stop_id

    def _extract_locations(self, normalized_message: str) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []

        matches.extend(
            self._extract_locations_from_items(
                normalized_message=normalized_message,
                items=station_service.stations,
                item_type="station",
                id_field="stop_id",
            )
        )

        matches.extend(
            self._extract_locations_from_items(
                normalized_message=normalized_message,
                items=station_service.places_without_train,
                item_type="place_without_train",
                id_field="place_id",
            )
        )

        matches = sorted(
            matches,
            key=lambda item: (item["start"], -item["length"]),
        )

        return self._remove_overlapping_matches(matches)

    def _extract_locations_from_items(
        self,
        normalized_message: str,
        items: list[dict[str, Any]],
        item_type: str,
        id_field: str,
    ) -> list[dict[str, Any]]:
        matches = []

        for item in items:
            forms = self._get_search_forms(item)

            for form in forms:
                pattern = r"(?<![a-z0-9])" + re.escape(form) + r"(?![a-z0-9])"

                for match in re.finditer(pattern, normalized_message):
                    matches.append(
                        {
                            "type": item_type,
                            "id": item.get(id_field),
                            "display_name": item.get("display_name"),
                            "matched_text": form,
                            "start": match.start(),
                            "end": match.end(),
                            "length": match.end() - match.start(),
                        }
                    )

        return matches

    def _get_search_forms(self, item: dict[str, Any]) -> list[str]:
        raw_values = []

        if item.get("display_name"):
            raw_values.append(item["display_name"])

        if item.get("official_name"):
            raw_values.append(item["official_name"])

        raw_values.extend(item.get("aliases", []))
        raw_values.extend(item.get("common_typos", []))

        normalized_values = []

        for value in raw_values:
            normalized = normalize_text(value)

            if len(normalized) >= 2:
                normalized_values.append(normalized)

        return sorted(set(normalized_values), key=len, reverse=True)

    def _remove_overlapping_matches(
        self,
        matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        selected = []
        used_ids = set()
        used_ranges: list[tuple[int, int]] = []

        for match in matches:
            unique_key = f"{match['type']}:{match['id']}"

            if unique_key in used_ids:
                continue

            overlaps = any(
                self._ranges_overlap(
                    match["start"],
                    match["end"],
                    start,
                    end,
                )
                for start, end in used_ranges
            )

            if overlaps:
                continue

            selected.append(match)
            used_ids.add(unique_key)
            used_ranges.append((match["start"], match["end"]))

        return selected

    def _ranges_overlap(
        self,
        start_a: int,
        end_a: int,
        start_b: int,
        end_b: int,
    ) -> bool:
        return start_a < end_b and start_b < end_a

    def _has_origin_marker_before(
        self,
        normalized_message: str,
        location: dict[str, Any],
    ) -> bool:
        return self._has_marker_before(
            normalized_message=normalized_message,
            location=location,
            markers=[
                "des de",
                "desde",
                "sortir de",
                "sortir d",
                "surt de",
                "surten de",
                "de",
                "d",
            ],
        )

    def _has_destination_marker_before(
        self,
        normalized_message: str,
        location: dict[str, Any],
    ) -> bool:
        return self._has_marker_before(
            normalized_message=normalized_message,
            location=location,
            markers=[
                "cap a",
                "fins a",
                "hasta",
                "anar a",
                "vaig a",
                "vull anar a",
                "a",
            ],
        )

    def _has_marker_before(
        self,
        normalized_message: str,
        location: dict[str, Any],
        markers: list[str],
    ) -> bool:
        before = normalized_message[: location["start"]].strip()
        last_words = " ".join(before.split()[-5:])

        for marker in markers:
            if last_words == marker or last_words.endswith(f" {marker}"):
                return True

        return False

    def _is_train_related(
        self,
        normalized_message: str,
        detected_locations: list[dict[str, Any]],
    ) -> bool:
        if self._contains_any(normalized_message, TRAIN_KEYWORDS):
            return True

        if detected_locations and self._contains_any(
            normalized_message,
            [
                "de",
                "des de",
                "desde",
                "a",
                "cap a",
                "fins a",
                "anar",
                "arribar",
                "sortir",
            ],
        ):
            return True

        # Permet respostes curtes de seguiment com "A Palma" o "Inca".
        if detected_locations and len(normalized_message.split()) <= 3:
            return True

        return False

    def _contains_any(self, text: str, words: list[str]) -> bool:
        normalized_words = [normalize_text(word) for word in words]

        return any(word in text for word in normalized_words)


intent_service = IntentService()