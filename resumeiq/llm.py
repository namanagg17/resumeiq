"""Thin wrapper around any OpenAI-compatible chat API (OpenAI, Gemini, etc.)."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when the API key or model is not configured."""


@dataclass
class LLMConfig:
    api_key: str
    model: str
    base_url: str | None = None
    temperature: float = 0.2


def load_config() -> LLMConfig:
    """Read settings from environment variables (see .env.example)."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConfigError(
            "No API key found. Copy .env.example to .env and set LLM_API_KEY."
        )
    return LLMConfig(
        api_key=api_key,
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("LLM_BASE_URL") or None,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
    )


def parse_json(text: str) -> dict:
    """Parse a JSON object from model output, tolerating ``` fences or extra text."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise ValueError(f"Model did not return JSON: {text[:200]!r}")


class LLMClient:
    """Sends prompts to the model. Swap in a fake client in tests."""

    def __init__(self, config: LLMConfig):
        from openai import OpenAI  # imported here so tests do not need a key

        self.config = config
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        messages = []
        if system.strip():
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as error:  # network / rate-limit errors
                last_error = error
                time.sleep(2 ** attempt)
        raise RuntimeError(f"LLM call failed after 3 attempts: {last_error}")

    def chat_json(self, system: str, user: str) -> dict:
        return parse_json(self.chat(system, user, json_mode=True))
