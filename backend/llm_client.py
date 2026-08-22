"""LLM transport clients for orchestration nodes."""

from __future__ import annotations

import os
from typing import Any

from google import genai


class GeminiClient:
    """Minimal Gemini-backed client that satisfies the node generate protocol."""

    def __init__(self, api_key: str | None = None, model_name: str = "gemini-3.5-flash-lite") -> None:
        self.model_name = model_name
        self.explicit_api_key = api_key

    def generate(self, prompt: str) -> str:
        try:
            # Dynamically resolve the API key on every call (checks os.environ or state)
            resolved_api_key = self.explicit_api_key or os.getenv("GEMINI_API_KEY")
            if not resolved_api_key:
                raise ValueError("No API key was provided. Please set GEMINI_API_KEY or save it in settings.")
            
            # Instantiate the client right here with the fresh key
            client = genai.Client(api_key=resolved_api_key)
            response = client.models.generate_content(
                model=self.model_name, 
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.4,
                )
            )
            
            text = getattr(response, "text", None)
            if isinstance(text, str):
                return text
            return str(response)
        except Exception as exc:
            return f"ERROR: API call failed - {exc}"
