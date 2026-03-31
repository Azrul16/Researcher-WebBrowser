from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class HistoryManager:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            self._write([])

    def load(self) -> List[Dict[str, str]]:
        try:
            payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return payload if isinstance(payload, list) else []

    def add(self, title: str, url: str) -> None:
        if not url or url.startswith("about:"):
            return
        history = [item for item in self.load() if item.get("url") != url]
        history.insert(
            0,
            {
                "title": title or url,
                "url": url,
                "visited_at": datetime.now().isoformat(timespec="seconds"),
            },
        )
        self._write(history[:500])

    def _write(self, payload) -> None:
        self.data_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
