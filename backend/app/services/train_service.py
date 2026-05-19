import json
from pathlib import Path
from typing import Any, Optional


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SCHEDULES_FILE = DATA_DIR / "schedules_sample.json"


def load_json_file(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"No s'ha trobat el fitxer: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def time_to_minutes(time_str: str) -> int:
    """
    Converteix HH:MM a minuts des de mitjanit.
    Exemple: 08:30 -> 510
    """
    hour, minute = time_str.split(":")
    return int(hour) * 60 + int(minute)


def minutes_to_time(minutes: int) -> str:
    """
    Converteix minuts des de mitjanit a HH:MM.
    """
    minutes = minutes % (24 * 60)
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


class TrainService:
    def __init__(self) -> None:
        self.data = load_json_file(SCHEDULES_FILE)
        self.routes = self.data.get("routes", [])
        self.service_calendars = self.data.get("service_calendars", [])
        self.trips = self.data.get("trips", [])

        self.route_index = {
            route["route_id"]: route
            for route in self.routes
        }

    def search_next_departure(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        after_time: str,
        service_id: Optional[str] = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Cerca els pròxims trens/metros després d'una hora concreta.
        """
        results = []

        for trip in self._get_candidate_trips(service_id):
            segment = self._extract_segment(trip, origin_stop_id, destination_stop_id)

            if not segment:
                continue

            departure_minutes = time_to_minutes(segment["origin"]["time"])
            after_minutes = time_to_minutes(after_time)

            if departure_minutes >= after_minutes:
                results.append(segment)

        results = self._sort_by_departure(results)
        return results[:limit]

    def search_trains_in_window(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        start_time: str,
        end_time: str,
        service_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Cerca trens/metros amb sortida dins una finestra horària.
        Exemple: de 07:00 a 09:00.
        """
        results = []

        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)

        for trip in self._get_candidate_trips(service_id):
            segment = self._extract_segment(trip, origin_stop_id, destination_stop_id)

            if not segment:
                continue

            departure_minutes = time_to_minutes(segment["origin"]["time"])

            if start_minutes <= departure_minutes <= end_minutes:
                results.append(segment)

        return self._sort_by_departure(results)

    def search_arrival_before(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        arrival_time: str,
        service_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Cerca trens/metros que arriben abans d'una hora concreta.
        Exemple: arribar a Palma abans de les 09:00.
        """
        results = []

        target_minutes = time_to_minutes(arrival_time)

        for trip in self._get_candidate_trips(service_id):
            segment = self._extract_segment(trip, origin_stop_id, destination_stop_id)

            if not segment:
                continue

            arrival_minutes = time_to_minutes(segment["destination"]["time"])

            if arrival_minutes <= target_minutes:
                results.append(segment)

        results = self._sort_by_arrival(results)
        return results[:limit]

    def search_departure_after(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: str,
        service_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Cerca trens/metros que surten després d'una hora concreta.
        """
        results = []

        target_minutes = time_to_minutes(departure_time)

        for trip in self._get_candidate_trips(service_id):
            segment = self._extract_segment(trip, origin_stop_id, destination_stop_id)

            if not segment:
                continue

            departure_minutes = time_to_minutes(segment["origin"]["time"])

            if departure_minutes >= target_minutes:
                results.append(segment)

        results = self._sort_by_departure(results)
        return results[:limit]

    def search_departures_from_station(
        self,
        origin_stop_id: str,
        start_time: str,
        end_time: str,
        service_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Cerca sortides des d'una estació dins una finestra horària.
        Agafa com a destinació el final del trajecte.
        """
        results = []

        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)

        for trip in self._get_candidate_trips(service_id):
            stop_times = trip.get("stop_times", [])

            if not stop_times:
                continue

            final_stop_id = stop_times[-1].get("stop_id")
            segment = self._extract_segment(trip, origin_stop_id, final_stop_id)

            if not segment:
                continue

            departure_minutes = time_to_minutes(segment["origin"]["time"])

            if start_minutes <= departure_minutes <= end_minutes:
                results.append(segment)

        results = self._sort_by_departure(results)
        return results[:limit]

    def search_arrivals_to_station(
        self,
        destination_stop_id: str,
        start_time: str,
        end_time: str,
        service_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Cerca arribades a una estació dins una finestra horària.
        Agafa com a origen l'inici del trajecte.
        """
        results = []

        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)

        for trip in self._get_candidate_trips(service_id):
            stop_times = trip.get("stop_times", [])

            if not stop_times:
                continue

            first_stop_id = stop_times[0].get("stop_id")
            segment = self._extract_segment(trip, first_stop_id, destination_stop_id)

            if not segment:
                continue

            arrival_minutes = time_to_minutes(segment["destination"]["time"])

            if start_minutes <= arrival_minutes <= end_minutes:
                results.append(segment)

        results = self._sort_by_arrival(results)
        return results[:limit]

    def _get_candidate_trips(
        self,
        service_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Filtra per service_id si s'indica.
        Si no s'indica, retorna tots els trips.
        """
        if service_id is None:
            return self.trips

        return [
            trip
            for trip in self.trips
            if trip.get("service_id") == service_id
        ]

    def _extract_segment(
        self,
        trip: dict[str, Any],
        origin_stop_id: str,
        destination_stop_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Comprova si un trip conté origen i destinació en l'ordre correcte.
        Si sí, retorna només el tram que interessa.
        """
        stop_times = trip.get("stop_times", [])

        origin_stop = None
        destination_stop = None

        for stop_time in stop_times:
            if stop_time.get("stop_id") == origin_stop_id:
                origin_stop = stop_time

            if stop_time.get("stop_id") == destination_stop_id:
                destination_stop = stop_time

        if not origin_stop or not destination_stop:
            return None

        origin_sequence = origin_stop.get("sequence")
        destination_sequence = destination_stop.get("sequence")

        if origin_sequence is None or destination_sequence is None:
            return None

        if origin_sequence >= destination_sequence:
            return None

        route_id = trip.get("route_id")
        route = self.route_index.get(route_id, {})

        departure_time = origin_stop["time"]
        arrival_time = destination_stop["time"]

        duration_minutes = time_to_minutes(arrival_time) - time_to_minutes(departure_time)

        return {
            "trip_id": trip.get("trip_id"),
            "route_id": route_id,
            "route_name": route.get("display_name", route_id),
            "service_id": trip.get("service_id"),
            "direction_id": trip.get("direction_id"),
            "headsign": trip.get("headsign"),
            "bikes_allowed": trip.get("bikes_allowed"),
            "origin": {
                "stop_id": origin_stop_id,
                "sequence": origin_sequence,
                "time": departure_time,
            },
            "destination": {
                "stop_id": destination_stop_id,
                "sequence": destination_sequence,
                "time": arrival_time,
            },
            "duration_minutes": duration_minutes,
            "source_file": trip.get("source_file"),
            "source_page": trip.get("source_page"),
        }

    def _sort_by_departure(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return sorted(
            results,
            key=lambda result: time_to_minutes(result["origin"]["time"]),
        )

    def _sort_by_arrival(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return sorted(
            results,
            key=lambda result: time_to_minutes(result["destination"]["time"]),
        )


train_service = TrainService()