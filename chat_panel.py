from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, Qt, QUrl
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QColor


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class ChatBridge(QObject):
    messageSubmitted = pyqtSignal(str)
    quickActionRequested = pyqtSignal(str)

    @pyqtSlot(str)
    def submitMessage(self, message: str) -> None:
        self.messageSubmitted.emit(message)

    @pyqtSlot(str)
    def requestQuickAction(self, prompt: str) -> None:
        self.quickActionRequested.emit(prompt)


class ChatPanel(QWebEngineView):
    message_submitted = pyqtSignal(str)
    quick_action_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loaded = False
        self._pending_messages: list[tuple[str, str]] = []

        self.bridge = ChatBridge()
        self.bridge.messageSubmitted.connect(self.message_submitted.emit)
        self.bridge.quickActionRequested.connect(self.quick_action_requested.emit)

        channel = QWebChannel(self.page())
        channel.registerObject("chatBridge", self.bridge)
        self.page().setWebChannel(channel)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.loadFinished.connect(self._on_load_finished)
        self._load_ui()

    def _load_ui(self) -> None:
        html_path = ASSETS_DIR / "chat_panel.html"
        html = html_path.read_text(encoding="utf-8")
        self.setHtml(html, QUrl.fromLocalFile(str(ASSETS_DIR) + "/"))

    def _on_load_finished(self, ok: bool) -> None:
        self._loaded = ok
        if not ok:
            return
        while self._pending_messages:
            sender, text = self._pending_messages.pop(0)
            self.add_message(sender, text)

    def add_message(self, sender: str, text: str) -> None:
        if not self._loaded:
            self._pending_messages.append((sender, text))
            return

        sender_json = json.dumps(sender)
        text_json = json.dumps(text)
        self.page().runJavaScript(f"window.chatPanel.addMessage({sender_json}, {text_json});")
