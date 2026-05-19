import json
import re
from typing import Any

from google import genai
from google.genai import types

from app.config import settings


PLACEHOLDER_API_KEYS = {
    "AIzaSyArqs4VXTrzxDti2ahgRsfsCx6pcwxdIX0",
}


class LLMService:
    """
    Servei genèric per parlar amb Gemini.

    Responsabilitat:
    - enviar prompts a Gemini
    - demanar resposta JSON
    - parsejar la resposta
    - fallar clarament si no hi ha clau o si Gemini retorna malament
    """

    def __init__(self) -> None:
        self.model = settings.gemini_model
        self.api_key = settings.gemini_api_key
        self.client = None

        if self.api_key and self.api_key not in PLACEHOLDER_API_KEYS:
            self.client = genai.Client(api_key=self.api_key)

    def get_status(self) -> dict[str, Any]:
        api_key_preview = None

        if self.api_key:
            if len(self.api_key) > 8:
                api_key_preview = f"{self.api_key[:4]}...{self.api_key[-4:]}"
            else:
                api_key_preview = "***"

        return {
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "api_key_preview": api_key_preview,
            "is_placeholder_key": self.api_key in PLACEHOLDER_API_KEYS,
            "is_available": self.is_available(),
        }

    def is_available(self) -> bool:
        return self.client is not None

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("Gemini no està configurat. Revisa GEMINI_API_KEY al fitxer .env.")

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        text = response.text or ""

        return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """
        Gemini hauria de tornar JSON pur, però aquest parser és tolerant
        per si algun dia torna ```json ... ```.
        """
        cleaned = text.strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise ValueError(f"Gemini no ha retornat JSON vàlid: {cleaned}") from error

        if not isinstance(parsed, dict):
            raise ValueError("Gemini ha retornat JSON, però no és un objecte.")

        return parsed


llm_service = LLMService()