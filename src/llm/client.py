"""Small Gemini API wrapper with safe configuration and error handling."""

from __future__ import annotations

import os

from dotenv import load_dotenv


# Load environment variables from the project .env file.
load_dotenv()


DEFAULT_MODEL = "gemini-3.5-flash-lite"


class GeminiClientError(RuntimeError):
    """A safe, user-facing Gemini integration error that never includes secrets."""


class GeminiClient:
    """Generate JSON text with Gemini; business logic remains outside this client."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._api_key = os.getenv("GEMINI_API_KEY")
        self._client = None
        self._types = None

    def _initialize(self) -> None:
        if not self._api_key:
            raise GeminiClientError(
                "Gemini is not configured: GEMINI_API_KEY is missing."
            )

        if self._client is not None:
            return

        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise GeminiClientError(
                "Gemini SDK is unavailable. Install the project requirements."
            ) from error

        try:
            self._client = genai.Client(api_key=self._api_key)
            self._types = types
        except Exception as error:
            raise GeminiClientError(
                "Gemini client initialization failed."
            ) from error

    def generate_json(self, prompt: str) -> str:
        """Request JSON text with Gemini."""
        self._initialize()

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )

            if not response.text:
                raise GeminiClientError(
                    "Gemini returned an empty response."
                )

            return response.text

        except GeminiClientError:
            raise

        except Exception as error:
            raise GeminiClientError(
                "Gemini generation failed or the service is unavailable."
            ) from error