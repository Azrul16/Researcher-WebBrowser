from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, List
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from browser_window import BrowserWindow


class BrowserTools:
    def __init__(self, window: "BrowserWindow"):
        self.window = window

    def scholar_url(self, query: str) -> str:
        template = self.window.settings.get("search_url", "https://scholar.google.com/scholar?q={query}")
        return template.format(query=quote_plus(query))

    def search_google_scholar(self, query: str) -> str:
        self.window.open_url(self.scholar_url(query))
        return f"Opened Google Scholar results for: {query}"

    def open_new_tab(self, url: str) -> str:
        self.window.add_new_tab(url=url, make_current=True)
        return f"Opened a new tab: {url}"

    def bookmark_current_page(self) -> str:
        return self.window.add_current_page_to_bookmarks()

    def pin_current_tab(self) -> str:
        return self.window.toggle_pin_current_tab(force_pin=True)

    def list_open_tabs(self) -> List[str]:
        return self.window.get_tab_descriptions()

    def get_current_url(self) -> str:
        current_tab = self.window.current_browser_tab()
        return current_tab.url().toString() if current_tab else ""

    def get_current_page_text(self, callback: Callable[[str], None]) -> None:
        current_tab = self.window.current_browser_tab()
        if not current_tab:
            callback("")
            return
        current_tab.get_page_text(callback)

    def summarize_current_page(self, callback: Callable[[str], None]) -> None:
        def _on_text(text: str) -> None:
            cleaned = re.sub(r"\s+", " ", text).strip()
            callback(cleaned[:8000] if cleaned else "")

        self.get_current_page_text(_on_text)
