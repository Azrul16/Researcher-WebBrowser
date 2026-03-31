from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_SETTINGS = {
    "homepage": "https://scholar.google.com/",
    "search_url": "https://scholar.google.com/scholar?q={query}",
    "proxy_enabled": False,
    "proxy_label": "Direct",
    "proxy_host": "",
    "proxy_port": 8080,
    "proxy_username": "",
    "proxy_password": "",
    "splitter_sizes": [980, 320],
    "window_width": 1440,
    "window_height": 900,
}


class SettingsManager:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            self.save(DEFAULT_SETTINGS)

    def load(self) -> Dict[str, Any]:
        try:
            loaded = json.loads(self.data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = {}
        return {**DEFAULT_SETTINGS, **loaded}

    def save(self, settings: Dict[str, Any]) -> None:
        payload = {**DEFAULT_SETTINGS, **settings}
        self.data_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
