from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class BookmarkManager:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            self._write([])

    def load(self) -> List[Dict[str, str]]:
        try:
            return json.loads(self.data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def save(self, bookmarks: List[Dict[str, str]]) -> None:
        self._write(bookmarks)

    def add(self, title: str, url: str) -> None:
        bookmarks = self.load()
        if any(item["url"] == url for item in bookmarks):
            return
        bookmarks.append({"title": title or url, "url": url})
        self._write(bookmarks)

    def remove(self, url: str) -> bool:
        bookmarks = self.load()
        filtered = [item for item in bookmarks if item.get("url") != url]
        if len(filtered) == len(bookmarks):
            return False
        self._write(filtered)
        return True

    def contains(self, url: str) -> bool:
        if not url:
            return False
        return any(item.get("url") == url for item in self.load())

    def _write(self, payload) -> None:
        self.data_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
