"""
LLM provider abstraction.

Groq / OpenAI-compatible providers → openai SDK (different base_url)
Anthropic → anthropic SDK (different message format)

Usage:
    client = LLMClient()
    text = client.get_completion([{"role": "user", "content": "Hello"}])
"""

import json
from config import get_settings

settings = get_settings()


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        self._client = self._build_client()

    def _build_client(self):
        if self.provider == "anthropic":
            from anthropic import Anthropic
            return Anthropic(api_key=settings.llm_api_key)
        else:
            # Groq, OpenAI, Together, Fireworks — all speak OpenAI protocol
            from openai import OpenAI
            return OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url if self.provider != "openai" else None,
            )

    def get_completion(self, messages: list[dict], temperature: float = 0.2) -> str:
        """Send messages, return assistant text."""
        if self.provider == "anthropic":
            return self._anthropic_completion(messages, temperature)
        return self._openai_completion(messages, temperature)

    def get_json_completion(self, messages: list[dict], temperature: float = 0.1) -> dict | list:
        """Like get_completion but parses the response as JSON."""
        raw = self.get_completion(messages, temperature)
        # Strip markdown code fences if the model wrapped the JSON
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw.strip())

    def get_vision_json_completion(
        self,
        image_bytes: bytes,
        prompt: str,
        system: str = "",
        mime_type: str = "image/png",
        temperature: float = 0.1,
    ) -> dict | list:
        """
        Send an image + prompt, return parsed JSON.

        Groq (llama-4-scout) and OpenAI support the vision content block format.
        Anthropic uses its own SDK format.
        """
        import base64
        b64 = base64.standard_b64encode(image_bytes).decode()

        if self.provider == "anthropic":
            raw = self._anthropic_vision_completion(b64, mime_type, prompt, system, temperature)
        else:
            # OpenAI-compatible (Groq, OpenAI, etc.)
            raw = self._openai_vision_completion(b64, mime_type, prompt, system, temperature)

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw.strip())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
            max_tokens=4096,
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

    def _openai_completion(self, messages: list[dict], temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    def _anthropic_completion(self, messages: list[dict], temperature: float) -> str:
        # Anthropic separates system messages from the messages list
        system_text = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            else:
                filtered.append(m)

        kwargs = dict(
            model=self.model,
            max_tokens=4096,
            messages=filtered,
            temperature=temperature,
        )
        if system_text:
            kwargs["system"] = system_text

        response = self._client.messages.create(**kwargs)
        return response.content[0].text.strip()
