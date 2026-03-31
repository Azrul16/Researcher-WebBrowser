from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Researcher"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"
