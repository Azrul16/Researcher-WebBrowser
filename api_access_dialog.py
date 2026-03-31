from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)


class ApiAccessDialog(QDialog):
    def __init__(self, proxy_url: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Up AI Access")
        self.setModal(True)
        self.resize(520, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Connect Researcher to AI")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #f4f6fb;")
        layout.addWidget(title)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setFrameStyle(0)
        body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.setStyleSheet(
            """
            QTextEdit {
                background: transparent;
                color: #aeb5c2;
                font-size: 13px;
                border: none;
            }
            """
        )
        if proxy_url:
            body.setPlainText(
                "This app can use a backend proxy for AI requests. "
                "If the proxy is unavailable, you can still enter your own Groq API key and it will be stored securely on this PC."
            )
        else:
            body.setPlainText(
                "Enter a Groq API key to unlock AI features. "
                "The key will be stored securely on this computer using the OS credential store, not bundled inside the app."
            )
        layout.addWidget(body)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setPlaceholderText("Paste Groq API key here")
        self.input.setStyleSheet(
            """
            QLineEdit {
                min-height: 42px;
                padding: 0 14px;
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.10);
                background: #20222a;
                color: #f4f6fb;
            }
            """
        )
        layout.addWidget(self.input)

        self.notice = QLabel("Leave blank to continue without local AI setup.")
        self.notice.setStyleSheet("color: #8d95a3; font-size: 12px;")
        layout.addWidget(self.notice)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save Key")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Skip")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("QDialog { background: #17181d; }")

    def api_key(self) -> str:
        return self.input.text().strip()
