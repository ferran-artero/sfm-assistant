import json
import re
import unicodedata
from difflib import get_close_matches
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATIONS_FILE = DATA_DIR / "stations.json"
PLACES_WITHOUT_TRAIN_FILE = DATA_DIR / "places_without_train.json"


def normalize_text(text: str) -> str:
    """
    Normalitza text per comparar noms d'estacions:
    - minúscules
    - sense accents
    - sense apòstrofs ni signes especials
    - espais unificats
    """
    if not text:
        return ""

    text = text.strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))

    text = text.replace("’", "'")
    text = text.replace("`", "'")
    text = text.replace("´", "'")

    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def compact_text(text: str) -> str:
    """
    Versió sense espais per detectar casos com:
    - sapobla -> sa pobla
    - parcbit -> parc bit
    """
    return normalize_text(text).replace(" ", "")


def load_json_file(file_path: Path) -> list[dict[str, Any]]:
    if not file_path.exists():
        raise FileNotFoundError(f"No s'ha trobat el fitxer: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


class StationService:
    def __init__(self) -> None:
        self.stations = load_json_file(STATIONS_FILE)
        self.places_without_train = load_json_file(PLACES_WITHOUT_TRAIN_FILE)

        self.station_index = self._build_index(self.stations, item_type="station")
        self.place_index = self._build_index(self.places_without_train, item_type="place")

        self.all_station_keys = list(self.station_index.keys())
        self.all_place_keys = list(self.place_index.keys())

    def _build_index(
        self,
        items: list[dict[str, Any]],
        item_type: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Crea un índex de cerca a partir de:
        - display_name
        - official_name
        - aliases
        - common_typos
        - versions compactes sense espais
        """
        index: dict[str, list[dict[str, Any]]] = {}

        for item in items:
            values = []

            if item.get("display_name"):
                values.append(item["display_name"])

            if item.get("official_name"):
                values.append(item["official_name"])

            values.extend(item.get("aliases", []))
            values.extend(item.get("common_typos", []))

            for value in values:
                normalized = normalize_text(value)
                compact = compact_text(value)

                if normalized:
                    index.setdefault(normalized, []).append(item)

                if compact and compact != normalized:
                    index.setdefault(compact, []).append(item)

        return index

    def validate_station(self, query: str) -> dict[str, Any]:
        """
        Valida si el text de l'usuari correspon a:
        - una aturada vàlida
        - un lloc conegut sense tren
        - un possible error d'escriptura
        - un lloc desconegut
        """
        original_query = query
        normalized_query = normalize_text(query)
        compact_query = compact_text(query)

        if not normalized_query:
            return {
                "input": original_query,
                "normalized_input": normalized_query,
                "status": "empty",
                "is_valid": False,
                "message": "No s'ha indicat cap estació o lloc.",
            }

        station_matches = self._exact_matches(normalized_query, compact_query, self.station_index)
        place_matches = self._exact_matches(normalized_query, compact_query, self.place_index)

        if len(station_matches) == 1 and len(place_matches) == 0:
            station = station_matches[0]
            return self._valid_station_response(original_query, normalized_query, station)

        if len(station_matches) == 0 and len(place_matches) == 1:
            place = place_matches[0]
            return self._place_without_train_response(original_query, normalized_query, place)

        if len(station_matches) > 1 or len(place_matches) > 1 or (station_matches and place_matches):
            return self._ambiguous_response(
                original_query=original_query,
                normalized_query=normalized_query,
                station_matches=station_matches,
                place_matches=place_matches,
            )

        typo_suggestion = self._find_typo_suggestion(normalized_query)

        if typo_suggestion:
            return {
                "input": original_query,
                "normalized_input": normalized_query,
                "status": "typo_suggestion",
                "is_valid": False,
                "suggestion": typo_suggestion,
                "message": f"Volies dir {typo_suggestion['display_name']}?",
            }

        return {
            "input": original_query,
            "normalized_input": normalized_query,
            "status": "unknown_place",
            "is_valid": False,
            "message": (
                f"No he trobat '{original_query}' com a estació ni com a lloc conegut "
                "dins la demo."
            ),
        }

    def _exact_matches(
        self,
        normalized_query: str,
        compact_query: str,
        index: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        matches = []

        for key in {normalized_query, compact_query}:
            if key in index:
                matches.extend(index[key])

        return self._deduplicate_items(matches)

    def _deduplicate_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_ids = set()
        unique_items = []

        for item in items:
            item_id = item.get("stop_id") or item.get("place_id")

            if item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_items.append(item)

        return unique_items

    def _find_typo_suggestion(self, normalized_query: str) -> dict[str, Any] | None:
        station_match = get_close_matches(
            normalized_query,
            self.all_station_keys,
            n=1,
            cutoff=0.78,
        )

        if station_match:
            matched_key = station_match[0]
            station = self.station_index[matched_key][0]

            return {
                "type": "station",
                "stop_id": station.get("stop_id"),
                "display_name": station.get("display_name"),
                "matched_text": matched_key,
            }

        place_match = get_close_matches(
            normalized_query,
            self.all_place_keys,
            n=1,
            cutoff=0.82,
        )

        if place_match:
            matched_key = place_match[0]
            place = self.place_index[matched_key][0]

            return {
                "type": "place_without_train",
                "place_id": place.get("place_id"),
                "display_name": place.get("display_name"),
                "matched_text": matched_key,
            }

        return None

    def _valid_station_response(
        self,
        original_query: str,
        normalized_query: str,
        station: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "input": original_query,
            "normalized_input": normalized_query,
            "status": "valid_station",
            "is_valid": True,
            "stop_id": station.get("stop_id"),
            "display_name": station.get("display_name"),
            "official_name": station.get("official_name"),
            "modes": station.get("modes", []),
            "routes": station.get("routes", []),
            "message": f"{station.get('display_name')} és una aturada vàlida.",
        }

    def _place_without_train_response(
        self,
        original_query: str,
        normalized_query: str,
        place: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "input": original_query,
            "normalized_input": normalized_query,
            "status": "known_place_without_train",
            "is_valid": False,
            "place_id": place.get("place_id"),
            "display_name": place.get("display_name"),
            "official_name": place.get("official_name"),
            "reason": place.get("reason"),
            "suggested_stop_ids": place.get("suggested_stop_ids", []),
            "message": place.get(
                "message",
                f"{place.get('display_name')} no apareix com a aturada dins la xarxa carregada.",
            ),
        }

    def _ambiguous_response(
        self,
        original_query: str,
        normalized_query: str,
        station_matches: list[dict[str, Any]],
        place_matches: list[dict[str, Any]],
    ) -> dict[str, Any]:
        options = []

        for station in station_matches:
            options.append(
                {
                    "type": "station",
                    "id": station.get("stop_id"),
                    "display_name": station.get("display_name"),
                    "routes": station.get("routes", []),
                }
            )

        for place in place_matches:
            options.append(
                {
                    "type": "place_without_train",
                    "id": place.get("place_id"),
                    "display_name": place.get("display_name"),
                }
            )

        return {
            "input": original_query,
            "normalized_input": normalized_query,
            "status": "ambiguous",
            "is_valid": False,
            "options": options,
            "message": (
                f"'{original_query}' pot correspondre a més d'un lloc. "
                "Necessit aclarir a quin et refereixes."
            ),
        }


station_service = StationService()