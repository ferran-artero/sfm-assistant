import re
from datetime import datetime, timezone
from typing import Any


TIME_PATTERN = re.compile(r"\b([01]?\d|2[0-3])\s*(?::|h|\.)([0-5]\d)\b")
MAX_LOG_ENTRIES = 100


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HallucinationGuard:
    """
    Validador anti-al·lucinacions per a respostes generades per Gemini.

    Objectiu:
    - Detectar hores que apareixen a la resposta.
    - Comparar-les amb les hores verificades retornades pel Train Service.
    - Si Gemini ha inventat una hora, marcar la resposta com a no segura.
    - Guardar errors recents per debug.
    """

    def __init__(self) -> None:
        self.error_log: list[dict[str, Any]] = []

    def validate_response(
        self,
        response: str,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        detected_times = self.extract_times_from_text(response)
        allowed_times = self.extract_allowed_times_from_results(results)

        invented_times = sorted(detected_times - allowed_times)

        is_valid = len(invented_times) == 0

        validation = {
            "is_valid": is_valid,
            "detected_times": sorted(detected_times),
            "allowed_times": sorted(allowed_times),
            "invented_times": invented_times,
            "error": None,
        }

        if not is_valid:
            validation["error"] = (
                f"La resposta conté hores que no apareixen als resultats verificats: "
                f"{', '.join(invented_times)}"
            )

        return validation

    def assert_response_is_safe(
        self,
        response: str,
        results: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> None:
        validation = self.validate_response(
            response=response,
            results=results,
        )

        if validation["is_valid"]:
            return

        self.register_error(
            response=response,
            results=results,
            validation=validation,
            context=context,
        )

        raise ValueError(validation["error"])

    def extract_times_from_text(
        self,
        text: str,
    ) -> set[str]:
        """
        Extreu hores en formats com:
        - 08:30
        - 8:30
        - 08h30
        - 08.30

        Les normalitza sempre a HH:MM.
        """
        times = set()

        for match in TIME_PATTERN.finditer(text):
            hour = int(match.group(1))
            minute = int(match.group(2))

            times.add(f"{hour:02d}:{minute:02d}")

        return times

    def extract_allowed_times_from_results(
        self,
        results: list[dict[str, Any]],
    ) -> set[str]:
        """
        Extreu totes les hores verificades dels resultats del Train Service.
        Normalment són:
        - hora de sortida
        - hora d'arribada
        """
        allowed_times = set()

        for result in results:
            origin_time = result.get("origin", {}).get("time")
            destination_time = result.get("destination", {}).get("time")

            if origin_time:
                allowed_times.add(origin_time)

            if destination_time:
                allowed_times.add(destination_time)

        return allowed_times

    def register_error(
        self,
        response: str,
        results: list[dict[str, Any]],
        validation: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "timestamp": now_iso(),
            "response": response,
            "validation": validation,
            "context": context or {},
            "results_count": len(results),
            "trip_ids": [
                result.get("trip_id")
                for result in results
                if result.get("trip_id")
            ],
        }

        self.error_log.append(entry)

        if len(self.error_log) > MAX_LOG_ENTRIES:
            self.error_log = self.error_log[-MAX_LOG_ENTRIES:]

    def get_error_log(self) -> list[dict[str, Any]]:
        return self.error_log

    def clear_error_log(self) -> None:
        self.error_log = []


hallucination_guard = HallucinationGuard()