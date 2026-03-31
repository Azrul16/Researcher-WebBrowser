from __future__ import annotations

import os
from typing import Optional

import keyring

from app_paths import APP_NAME


SERVICE_NAME = APP_NAME
ACCOUNT_NAME = "groq_api_key"


def get_groq_api_key() -> Optional[str]:
    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        value = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        return None
    return value.strip() if value else None


def set_groq_api_key(api_key: str) -> bool:
    value = api_key.strip()
    if not value:
        return False
    try:
        keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, value)
    except Exception:
        return False
    return True


def delete_groq_api_key() -> bool:
    try:
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        return False
    return True
