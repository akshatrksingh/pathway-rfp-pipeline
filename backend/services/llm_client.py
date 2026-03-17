"""
LLM provider abstraction.

Groq / OpenAI-compatible providers → openai SDK (different base_url)
Anthropic → anthropic SDK (different message format)

All API calls are wrapped with exponential-backoff retry (3 attempts, 2s base).
"""

import json
import re
import time
from config import get_settings

settings = get_settings()

_MAX_RETRIES = 3
_RETRY_BASE  = 2  # seconds


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.model    = settings.llm_model
        self._client  = self._build_client()

    def _build_client(self):
        if self.provider == "anthropic":
            from anthropic import Anthropic
            return Anthropic(api_key=settings.llm_api_key)
        else:
            from openai import OpenAI
            return OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url if self.provider != "openai" else None,
            )

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    def _with_retry(self, fn, *args, **kwargs):
        """Call fn(*args, **kwargs) up to _MAX_RETRIES times with exponential backoff."""
        wait = _RETRY_BASE
        last_exc = None
        for attempt in range(_MAX_RETRIES):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(wait)
                    wait *= 2
        raise last_exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_completion(self, messages: list[dict], temperature: float = 0.2) -> str:
        """Send messages, return assistant text."""
        if self.provider == "anthropic":
            return self._with_retry(self._anthropic_completion, messages, temperature)
        return self._with_retry(self._openai_completion, messages, temperature)

    def get_json_completion(self, messages: list[dict], temperature: float = 0.1) -> dict | list:
        """Like get_completion but parses the response as JSON."""
        raw = self.get_completion(messages, temperature)
        raw = self._extract_json_text(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return json.loads(raw, strict=False)

    def get_vision_json_completion(
        self,
        image_bytes: bytes,
        prompt: str,
        system: str = "",
        mime_type: str = "image/png",
        temperature: float = 0.1,
    ) -> dict | list:
        """Send an image + prompt, return parsed JSON."""
        import base64
        b64 = base64.standard_b64encode(image_bytes).decode()

        if self.provider == "anthropic":
            raw = self._with_retry(
                self._anthropic_vision_completion, b64, mime_type, prompt, system, temperature
            )
        else:
            raw = self._with_retry(
                self._openai_vision_completion, b64, mime_type, prompt, system, temperature
            )

        raw = self._extract_json_text(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return json.loads(raw, strict=False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_text(raw: str) -> str:
        raw = raw.strip()
        fence = re.search(r"```(?:\w+)?\s*\n?([\s\S]*?)```", raw)
        if fence:
            return fence.group(1).strip()
        obj = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if obj:
            return obj.group(1).strip()
        return raw

    def _openai_completion(self, messages: list[dict], temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=8192,
        )
        return response.choices[0].message.content.strip()

    def _anthropic_completion(self, messages: list[dict], temperature: float) -> str:
        system_text = ""
        filtered    = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            else:
                filtered.append(m)

        kwargs = dict(
            model=self.model,
            max_tokens=8192,
            messages=filtered,
            temperature=temperature,
        )
        if system_text:
            kwargs["system"] = system_text

        response = self._client.messages.create(**kwargs)
        return response.content[0].text.strip()

    def _openai_vision_completion(
        self, b64: str, mime_type: str, prompt: str, system: str, temperature: float
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                {"type": "text", "text": prompt},
            ],
        })
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=8192,
        )
        return response.choices[0].message.content.strip()

    def _anthropic_vision_completion(
        self, b64: str, mime_type: str, prompt: str, system: str, temperature: float
    ) -> str:
        kwargs = dict(
            model=self.model,
            max_tokens=8192,
            temperature=temperature,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        if system:
            kwargs["system"] = system
        response = self._client.messages.create(**kwargs)
        return response.content[0].text.strip()
