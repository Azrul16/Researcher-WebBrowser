from __future__ import annotations

import os
from typing import Optional

import requests

from credential_store import get_groq_api_key


class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.proxy_url = os.getenv("RESEARCHER_PROXY_URL", "").strip().rstrip("/")
        self.proxy_token = os.getenv("RESEARCHER_PROXY_TOKEN", "").strip()
        self.api_key = api_key or get_groq_api_key()
        self.model = model

    @property
    def enabled(self) -> bool:
        return bool(self.proxy_url or self.api_key)

    @property
    def mode_label(self) -> str:
        if self.proxy_url:
            return "backend proxy"
        if self.api_key:
            return "local Groq key"
        return "not configured"

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        if not self.enabled:
            raise RuntimeError(
                "AI is not configured. Set a backend proxy URL or add a Groq API key to enable AI replies."
            )

        if self.proxy_url:
            headers = {"Content-Type": "application/json"}
            if self.proxy_token:
                headers["X-Researcher-Token"] = self.proxy_token
            response = requests.post(
                f"{self.proxy_url}/api/chat",
                headers=headers,
                json={
                    "model": self.model,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                },
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            return payload["reply"].strip()

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"].strip()
