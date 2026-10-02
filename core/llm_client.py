"""LLM Client module for conversational Dialogue mode.

Supports Google Gemini Flash API via google-genai SDK or local Ollama endpoint via requests.
Provides fallback mock response with friendly setup instructions if no API key or Ollama endpoint is configured.
"""

import os
from typing import Optional

import requests


class LLMClient:
    """Configurable LLM client for handling conversational dialogue queries."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        ollama_url: Optional[str] = None,
        ollama_model: str = "llama3",
    ) -> None:
        """Initialize LLMClient.

        Args:
            gemini_api_key: Gemini API key. Defaults to GEMINI_API_KEY env var.
            ollama_url: Ollama base URL (e.g. 'http://localhost:11434'). Defaults to OLLAMA_URL env var.
            ollama_model: Ollama model name. Defaults to 'llama3'.
        """
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_URL")
        self.ollama_model = ollama_model

        self.gemini_client = None
        self._init_gemini()

    def _init_gemini(self) -> None:
        """Initialize google-genai client if API key is provided."""
        if not self.gemini_api_key:
            return

        try:
            from google import genai  # type: ignore

            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        except Exception:
            self.gemini_client = None

    def query(self, prompt: str) -> str:
        """Send prompt to configured LLM (Gemini -> Ollama -> Mock Fallback).

        Args:
            prompt: User prompt or query string.

        Returns:
            Response text from LLM or fallback message.
        """
        if not prompt or not prompt.strip():
            return "Пустой запрос"

        # Strategy 1: Google Gemini Flash API
        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception as e:
                # If Gemini fails, try Ollama or fallback
                pass

        # Strategy 2: Local Ollama Endpoint
        if self.ollama_url:
            try:
                url = f"{self.ollama_url.rstrip('/')}/api/generate"
                payload = {
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                }
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response")
                    if response_text:
                        return response_text.strip()
            except Exception:
                pass

        # Strategy 3: Mock Fallback with friendly setup instructions
        return (
            "[Режим Диалога] API-ключ Gemini (GEMINI_API_KEY) или Ollama (OLLAMA_URL) не настроен.\n"
            "Задайте переменную окружения GEMINI_API_KEY для подключения ИИ или запустите Ollama."
        )


# Default global client instance
_default_client: Optional[LLMClient] = None


def get_llm_response(prompt: str) -> str:
    """Module-level function to handle dialogue queries.

    Args:
        prompt: Input transcription string.

    Returns:
        LLM response string or setup instructions.
    """
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client.query(prompt)
