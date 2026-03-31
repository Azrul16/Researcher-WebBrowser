from __future__ import annotations

import re
from threading import Thread

from PyQt6.QtCore import QObject, pyqtSignal

from groq_client import GroqClient
from tools import BrowserTools


class AgentController(QObject):
    status = pyqtSignal(str)
    reply_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tools: BrowserTools, groq_client: GroqClient):
        super().__init__()
        self.tools = tools
        self.groq_client = groq_client

    def handle_message(self, message: str) -> None:
        message = message.strip()
        if not message:
            return

        lower = message.lower()
        search_match = re.search(r"(search scholar for|find papers on|find recent papers on|search for)\s+(.*)", lower)

        if search_match:
            query = message[search_match.start(2):].strip()
            self.status.emit("Searching Google Scholar...")
            self.reply_ready.emit(self.tools.search_google_scholar(query))
            return

        if self._looks_like_url(message):
            self.status.emit("Opening the link in the browser...")
            self.reply_ready.emit(self.tools.open_new_tab(self._normalize_url(message)))
            return

        if "bookmark" in lower:
            self.status.emit("Saving this page to bookmarks...")
            self.reply_ready.emit(self.tools.bookmark_current_page())
            return

        if "pin" in lower and "tab" in lower:
            self.status.emit("Pinning the current tab...")
            self.reply_ready.emit(self.tools.pin_current_tab())
            return

        if "show tabs" in lower or "list tabs" in lower:
            tab_lines = self.tools.list_open_tabs()
            self.reply_ready.emit("\n".join(tab_lines) if tab_lines else "There are no open tabs.")
            return

        if "summarize" in lower or "summary" in lower or "what is this page" in lower:
            self.status.emit("Reading the current page...")
            self.tools.summarize_current_page(self._summarize_with_optional_groq)
            return

        if self._should_treat_as_search(lower):
            self.status.emit("Searching Google Scholar...")
            self.reply_ready.emit(self.tools.search_google_scholar(message))
            return

        if self.groq_client.enabled:
            self.status.emit("Thinking...")
            self.tools.summarize_current_page(lambda page_text: self._answer_with_context(message, page_text))
            return

        self.reply_ready.emit(
            "I can search Google Scholar, summarize the current page, bookmark pages, pin the active tab, and list open tabs. "
            "Set up a backend proxy or add a Groq API key to unlock richer research answers."
        )

    def _looks_like_url(self, message: str) -> bool:
        return message.startswith(("http://", "https://")) or ("." in message and " " not in message)

    def _normalize_url(self, message: str) -> str:
        if message.startswith(("http://", "https://")):
            return message
        return f"https://{message}"

    def _should_treat_as_search(self, lower: str) -> bool:
        direct_commands = [
            "bookmark",
            "pin",
            "tab",
            "summarize",
            "summary",
            "what is this page",
            "show tabs",
            "list tabs",
            "open ",
            "close ",
            "switch ",
        ]
        return not any(token in lower for token in direct_commands)

    def _summarize_with_optional_groq(self, page_text: str) -> None:
        if not page_text.strip():
            self.reply_ready.emit("I could not read meaningful text from the current page yet.")
            return

        if not self.groq_client.enabled:
            self.reply_ready.emit(f"Page summary preview:\n\n{page_text[:900]}")
            return

        self.status.emit("Summarizing with Groq...")
        self._run_groq(
            "You are a concise academic research assistant. Summarize webpages into short, useful research notes.",
            f"Summarize this academic page for a researcher.\n\nPage text:\n{page_text}",
        )

    def _answer_with_context(self, user_message: str, page_text: str) -> None:
        if not page_text.strip():
            page_text = "No readable page text was available."
        self._run_groq(
            "You are an academic browser assistant. Answer clearly, mention when page context is weak, and stay concise.",
            f"User request: {user_message}\n\nCurrent page context:\n{page_text}",
        )

    def _run_groq(self, system_prompt: str, user_prompt: str) -> None:
        def _task() -> None:
            try:
                self.reply_ready.emit(self.groq_client.generate_reply(system_prompt, user_prompt))
            except Exception as exc:
                self.error.emit(str(exc))

        Thread(target=_task, daemon=True).start()
