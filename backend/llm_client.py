"""LLM transport clients for orchestration nodes."""

from __future__ import annotations

import os
from typing import Any

from google import genai


class GeminiClient:
    """Minimal Gemini-backed client that satisfies the node generate protocol."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-1.5-pro") -> None:
        self.model_name = model_name
        resolved_api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=resolved_api_key) if resolved_api_key else None

    def generate(self, prompt: str) -> str:
        try:
            if self.client is None:
                raise ValueError("No API key was provided. Please set GEMINI_API_KEY or pass api_key.")
            response: Any = self.client.models.generate_content(model=self.model_name, contents=prompt)
            text = getattr(response, "text", None)
            if isinstance(text, str):
                return text
            return str(response)
        except Exception as exc:
            return f"ERROR: API call failed - {exc}"
