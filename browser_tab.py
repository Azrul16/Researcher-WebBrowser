from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from safety_filter import classify_url


def blocked_page_html(url: str, category: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>Blocked</title>
      <style>
        body {{
          margin: 0;
          min-height: 100vh;
          display: grid;
          place-items: center;
          background: linear-gradient(180deg, #181922, #0f1016);
          color: #f5f4fb;
          font-family: Segoe UI, sans-serif;
        }}
        .card {{
          max-width: 640px;
          margin: 24px;
          padding: 28px;
          border-radius: 20px;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.08);
          box-shadow: 0 20px 50px rgba(0,0,0,0.28);
        }}
        h1 {{ margin: 0 0 12px; font-size: 28px; }}
        p {{ color: #c9c3d8; line-height: 1.6; }}
        code {{
          display: block;
          margin-top: 14px;
          padding: 12px 14px;
          border-radius: 12px;
          background: rgba(0,0,0,0.22);
          color: #8de0ff;
          word-break: break-all;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <h1>Blocked by Research Mode</h1>
        <p>This browser blocks <strong>{category}</strong> sites to keep the workspace focused on academic browsing.</p>
        <code>{url}</code>
      </div>
    </body>
    </html>
    """


class BrowserPage(QWebEnginePage):
    def __init__(self, create_tab_callback: Callable[[], "BrowserTab"], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._create_tab_callback = create_tab_callback

    def createWindow(self, _type):
        new_tab = self._create_tab_callback()
        return new_tab.view.page()

    def acceptNavigationRequest(self, url: QUrl, _type, is_main_frame: bool) -> bool:
        category = classify_url(url.toString())
        if is_main_frame and category:
            self.setHtml(blocked_page_html(url.toString(), category), QUrl("about:blank"))
            return False
        return super().acceptNavigationRequest(url, _type, is_main_frame)


class BrowserTab(QWidget):
    title_changed = pyqtSignal(str)
    url_changed = pyqtSignal(QUrl)
    load_progress = pyqtSignal(int)
    load_finished = pyqtSignal(bool)

    def __init__(self, create_tab_callback: Callable[[], "BrowserTab"], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_pinned = False
        self.view = QWebEngineView(self)
        self.view.setPage(BrowserPage(create_tab_callback, self.view))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.view.titleChanged.connect(self.title_changed.emit)
        self.view.urlChanged.connect(self.url_changed.emit)
        self.view.loadProgress.connect(self.load_progress.emit)
        self.view.loadFinished.connect(self.load_finished.emit)

    def set_url(self, url: str) -> None:
        self.view.setUrl(QUrl(url))

    def set_html(self, html: str, base_url: str = "about:blank") -> None:
        self.view.setHtml(html, QUrl(base_url))

    def url(self) -> QUrl:
        return self.view.url()

    def title(self) -> str:
        return self.view.title()

    def back(self) -> None:
        self.view.back()

    def forward(self) -> None:
        self.view.forward()

    def reload(self) -> None:
        self.view.reload()

    def get_page_text(self, callback: Callable[[str], None]) -> None:
        self.view.page().toPlainText(callback)
