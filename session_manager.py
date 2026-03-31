from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_SESSION = {
    "tabs": [],
    "current_index": 0,
}


class SessionManager:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            self.save(DEFAULT_SESSION)

    def load(self) -> Dict[str, Any]:
        try:
            loaded = json.loads(self.data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = {}
        return {**DEFAULT_SESSION, **loaded}

    def save(self, session: Dict[str, Any]) -> None:
        payload = {**DEFAULT_SESSION, **session}
        self.data_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
