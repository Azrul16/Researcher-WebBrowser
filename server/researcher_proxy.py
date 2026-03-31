from __future__ import annotations

import os

import requests
from flask import Flask, jsonify, request


app = Flask(__name__)


def _require_token() -> tuple[bool, tuple]:
    expected = os.getenv("RESEARCHER_PROXY_TOKEN", "").strip()
    if not expected:
        return True, ()
    provided = request.headers.get("X-Researcher-Token", "").strip()
    if provided == expected:
        return True, ()
    return False, (jsonify({"error": "Unauthorized"}), 401)


@app.post("/api/chat")
def chat():
    ok, failure = _require_token()
    if not ok:
        return failure

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Server Groq API key is missing."}), 500

    payload = request.get_json(silent=True) or {}
    system_prompt = str(payload.get("system_prompt", "")).strip()
    user_prompt = str(payload.get("user_prompt", "")).strip()
    model = str(payload.get("model", "llama-3.3-70b-versatile")).strip() or "llama-3.3-70b-versatile"

    if not user_prompt:
        return jsonify({"error": "user_prompt is required."}), 400

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()
    groq_payload = response.json()
    reply = groq_payload["choices"][0]["message"]["content"].strip()
    return jsonify({"reply": reply})


@app.get("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    host = os.getenv("RESEARCHER_PROXY_HOST", "127.0.0.1")
    port = int(os.getenv("RESEARCHER_PROXY_PORT", "8787"))
    app.run(host=host, port=port)
