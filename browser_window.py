from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from agent_controller import AgentController
from api_access_dialog import ApiAccessDialog
from app_paths import app_base_dir, user_data_dir
from credential_store import set_groq_api_key
from bookmark_manager import BookmarkManager
from browser_chrome import BrowserChrome
from browser_tab import BrowserTab
from chat_panel import ChatPanel
from groq_client import GroqClient
from history_manager import HistoryManager
from proxy_manager import ProxyManager
from session_manager import SessionManager
from safety_filter import initialize_blocklists
from settings_manager import SettingsManager
from tools import BrowserTools

BASE_DIR = app_base_dir()
DATA_DIR = user_data_dir()
FLOATING_CHAT_WIDTH = 760
FLOATING_CHAT_HEIGHT = 96
FLOATING_CHAT_BOTTOM_OFFSET = 28


class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Researcher")

        self.settings_manager = SettingsManager(DATA_DIR / "settings.json")
        self.session_manager = SessionManager(DATA_DIR / "session.json")
        self.bookmark_manager = BookmarkManager(DATA_DIR / "bookmarks.json")
        self.history_manager = HistoryManager(DATA_DIR / "history.json")
        self.settings = self.settings_manager.load()
        initialize_blocklists(DATA_DIR / "blocked_domains_cache.json")

        self.proxy_settings = self._settings_with_env_overrides()
        self.proxy_manager = ProxyManager(self.proxy_settings)
        self.proxy_manager.apply()

        self._build_ui()
        self._restore_window()
        self._restore_session()
        self.refresh_bookmark_menu()

        self.groq_client = self._configure_ai_access()
        self.tools = BrowserTools(self)
        self.agent_controller = AgentController(self.tools, self.groq_client)
        self.agent_controller.status.connect(lambda text: self.chat_panel.add_message("status", text))
        self.agent_controller.reply_ready.connect(lambda text: self.chat_panel.add_message("assistant", text))
        self.agent_controller.error.connect(self._show_agent_error)

        if self.tabs.count() == 0:
            self.add_new_tab(url=self.settings["homepage"], make_current=True)

    def _configure_ai_access(self) -> GroqClient:
        client = GroqClient()
        if client.proxy_url or client.api_key:
            return client

        dialog = ApiAccessDialog(proxy_url=os.getenv("RESEARCHER_PROXY_URL", "").strip(), parent=self)
        if dialog.exec() and dialog.api_key():
            if set_groq_api_key(dialog.api_key()):
                self.statusBar().showMessage("Groq API key stored securely on this computer.", 4000)
                return GroqClient()
            self.statusBar().showMessage("Could not store the API key securely. Continuing without local AI.", 5000)
        return client

    def _settings_with_env_overrides(self, forced_enabled: Optional[bool] = None):
        settings = dict(self.settings)
        foxy_path = BASE_DIR / "FoxyProxy_config.json"

        env_proxy_enabled = os.getenv("PSTU_PROXY_ENABLED")
        if forced_enabled is not None:
            settings["proxy_enabled"] = forced_enabled
        elif env_proxy_enabled is not None:
            settings["proxy_enabled"] = env_proxy_enabled.lower() in {"1", "true", "yes"}
        if settings.get("proxy_enabled"):
            foxy_profile = ProxyManager.load_foxyproxy_profile(foxy_path)
            if foxy_profile:
                for key, value in foxy_profile.items():
                    if not settings.get(key):
                        settings[key] = value

        settings["proxy_host"] = os.getenv("PSTU_PROXY_HOST", settings["proxy_host"])
        settings["proxy_port"] = int(os.getenv("PSTU_PROXY_PORT", settings["proxy_port"]))
        settings["proxy_username"] = os.getenv("PSTU_PROXY_USERNAME", settings["proxy_username"])
        settings["proxy_password"] = os.getenv("PSTU_PROXY_PASSWORD", settings["proxy_password"])
        settings["proxy_label"] = "PSTU Proxy" if settings.get("proxy_enabled") else "Direct"
        return settings

    def _build_ui(self) -> None:
        container = QWidget()
        container.setObjectName("root")
        self.setCentralWidget(container)
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 0, 10, 10)
        left_layout.setSpacing(10)
        main_layout.addWidget(left_panel)

        self.browser_chrome = BrowserChrome()
        self.browser_chrome.back_requested.connect(self.go_back)
        self.browser_chrome.forward_requested.connect(self.go_forward)
        self.browser_chrome.reload_requested.connect(self.reload_page)
        self.browser_chrome.home_requested.connect(self.go_home)
        self.browser_chrome.new_tab_requested.connect(lambda: self.add_new_tab(make_current=True))
        self.browser_chrome.open_history_requested.connect(self.open_history_picker)
        self.browser_chrome.open_bookmarks_requested.connect(self.open_bookmark_picker)
        self.browser_chrome.add_bookmark_requested.connect(self.add_current_page_to_bookmarks)
        self.browser_chrome.navigate_requested.connect(self._navigate_from_chrome)
        self.browser_chrome.proxy_toggle_requested.connect(self.toggle_proxy_mode)
        self.browser_chrome.tab_selected.connect(self._set_current_tab)
        self.browser_chrome.tab_closed.connect(self.close_tab)
        left_layout.addWidget(self.browser_chrome)

        browser_stage = QWidget()
        browser_stage.setObjectName("browserStage")
        stage_layout = QGridLayout(browser_stage)
        stage_layout.setContentsMargins(0, 0, 0, FLOATING_CHAT_BOTTOM_OFFSET)
        stage_layout.setSpacing(0)
        left_layout.addWidget(browser_stage, 1)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("browserTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabBar().hide()
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._current_tab_changed)
        stage_layout.addWidget(self.tabs, 0, 0)

        self.chat_panel = ChatPanel()
        self.chat_panel.setMinimumWidth(FLOATING_CHAT_WIDTH)
        self.chat_panel.setMaximumWidth(FLOATING_CHAT_WIDTH)
        self.chat_panel.setMinimumHeight(FLOATING_CHAT_HEIGHT)
        self.chat_panel.setMaximumHeight(FLOATING_CHAT_HEIGHT)
        self.chat_panel.message_submitted.connect(self._submit_chat_message)
        self.chat_panel.quick_action_requested.connect(self._handle_quick_action)
        stage_layout.addWidget(self.chat_panel, 0, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

        self.setStatusBar(QStatusBar())
        self._apply_styles()
        self.browser_chrome.set_proxy_state(self.proxy_settings.get("proxy_enabled", False))

        QShortcut(QKeySequence.StandardKey.AddTab, self, activated=lambda: self.add_new_tab(make_current=True))
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.add_current_page_to_bookmarks)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=lambda: self.close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, activated=lambda: self.toggle_pin_current_tab(force_pin=None))

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #1c1b24;
            }
            QWidget#root {
                background: #212121;
            }
            QWidget#leftPanel {
                background: transparent;
            }
            QWidget#browserStage {
                background: transparent;
            }
            QTabWidget::pane {
                border: none;
                background: #1c1d22;
                border-radius: 18px;
            }
            QStatusBar {
                background: #191a1f;
                color: #9ca3af;
                border-top: 1px solid rgba(255, 255, 255, 0.04);
            }
            """
        )

    def add_new_tab(self, url: Optional[str] = None, make_current: bool = True, pinned: bool = False) -> BrowserTab:
        tab = BrowserTab(lambda: self.add_new_tab(make_current=True), self)
        tab.is_pinned = pinned
        tab.title_changed.connect(lambda title, t=tab: self._update_tab_title(t, title))
        tab.url_changed.connect(lambda qurl, t=tab: self._update_tab_url(t, qurl))
        tab.load_progress.connect(lambda progress, t=tab: self._handle_load_progress(t, progress))
        tab.load_finished.connect(lambda ok, t=tab: self._handle_load_finished(t, ok))

        index = self._pinned_insert_index() if pinned else self.tabs.count()
        self.tabs.insertTab(index, tab, "New Tab")
        if make_current:
            self.tabs.setCurrentWidget(tab)
        target_url = url or self.settings["homepage"]
        tab.set_url(target_url)
        self._sync_chrome()
        return tab

    def close_tab(self, index: int) -> None:
        if index < 0 or self.tabs.count() <= 1:
            return
        tab = self.tabs.widget(index)
        if getattr(tab, "is_pinned", False):
            self.statusBar().showMessage("Pinned tabs cannot be closed accidentally. Unpin first.", 3000)
            return
        self.tabs.removeTab(index)
        tab.deleteLater()
        self._sync_chrome()

    def current_browser_tab(self) -> Optional[BrowserTab]:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, BrowserTab) else None

    def _navigate_from_chrome(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self.open_url(self._resolve_input_to_url(text))

    def _resolve_input_to_url(self, text: str) -> str:
        if text.startswith("http://") or text.startswith("https://"):
            return text
        if "." in text and " " not in text:
            return f"https://{text}"
        return self.settings["search_url"].format(query=quote_plus(text))

    def open_url(self, url: str) -> None:
        current_tab = self.current_browser_tab()
        if current_tab is None:
            current_tab = self.add_new_tab(make_current=True)
        current_tab.set_url(url)

    def go_back(self) -> None:
        tab = self.current_browser_tab()
        if tab:
            tab.back()

    def go_forward(self) -> None:
        tab = self.current_browser_tab()
        if tab:
            tab.forward()

    def reload_page(self) -> None:
        tab = self.current_browser_tab()
        if tab:
            tab.reload()

    def go_home(self) -> None:
        self.open_url(self.settings["homepage"])

    def add_current_page_to_bookmarks(self) -> str:
        tab = self.current_browser_tab()
        if tab is None:
            return "There is no page open to bookmark."
        title = tab.title() or tab.url().toString()
        url = tab.url().toString()
        if not url:
            return "The current tab does not have a valid URL yet."
        if self.bookmark_manager.contains(url):
            self.bookmark_manager.remove(url)
            self.refresh_bookmark_menu()
            self._sync_bookmark_state()
            self.statusBar().showMessage("Bookmark removed.", 3000)
            return f"Removed bookmark: {title}"
        self.bookmark_manager.add(title, url)
        self.refresh_bookmark_menu()
        self._sync_bookmark_state()
        self.statusBar().showMessage("Bookmark saved.", 3000)
        return f"Bookmarked: {title}"

    def refresh_bookmark_menu(self) -> None:
        return

    def _open_library_tab(self, title: str, html: str) -> None:
        tab = self.add_new_tab(url="about:blank", make_current=True)
        tab.set_html(html)
        self._update_tab_title(tab, title)

    def _build_library_page(self, title: str, subtitle: str, items: list[dict], empty_text: str) -> str:
        cards = []
        for item in items:
            item_title = escape(item.get("title") or item.get("url") or title)
            item_url = escape(item.get("url", ""))
            meta = escape(item.get("meta", ""))
            cards.append(
                f"""
                <a class="card" href="{item_url}">
                  <div class="card-title">{item_title}</div>
                  <div class="card-url">{item_url}</div>
                  <div class="card-meta">{meta}</div>
                </a>
                """
            )

        items_html = "\n".join(cards) if cards else f'<div class="empty">{escape(empty_text)}</div>'
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1.0" />
          <title>{escape(title)}</title>
          <style>
            :root {{
              color-scheme: dark;
              --bg-top: #16181f;
              --bg-bottom: #101217;
              --panel: rgba(33, 36, 45, 0.88);
              --panel-strong: rgba(44, 48, 58, 0.96);
              --border: rgba(255, 255, 255, 0.08);
              --text: #f4f6fb;
              --muted: #9ea6b5;
              --accent: #8b3dff;
              --accent-soft: rgba(139, 61, 255, 0.18);
            }}
            * {{ box-sizing: border-box; }}
            html, body {{ margin: 0; min-height: 100%; font-family: "Segoe UI", sans-serif; }}
            body {{
              background:
                radial-gradient(circle at top left, rgba(139, 61, 255, 0.16), transparent 28%),
                linear-gradient(180deg, var(--bg-top), var(--bg-bottom));
              color: var(--text);
            }}
            .page {{
              max-width: 1040px;
              margin: 0 auto;
              padding: 44px 28px 120px;
            }}
            .hero {{
              margin-bottom: 24px;
              padding: 28px;
              border: 1px solid var(--border);
              border-radius: 28px;
              background: linear-gradient(180deg, rgba(45, 49, 59, 0.92), rgba(28, 31, 39, 0.94));
              box-shadow: 0 22px 60px rgba(0, 0, 0, 0.32);
            }}
            .eyebrow {{
              margin-bottom: 10px;
              color: #c69cff;
              font-size: 12px;
              font-weight: 700;
              letter-spacing: 0.12em;
              text-transform: uppercase;
            }}
            h1 {{
              margin: 0;
              font-size: 34px;
              line-height: 1.1;
            }}
            .subtitle {{
              margin-top: 12px;
              color: var(--muted);
              font-size: 15px;
              line-height: 1.6;
            }}
            .list {{
              display: grid;
              gap: 14px;
            }}
            .card {{
              display: block;
              padding: 18px 20px;
              border: 1px solid var(--border);
              border-radius: 22px;
              background: linear-gradient(180deg, var(--panel), var(--panel-strong));
              color: inherit;
              text-decoration: none;
              transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
              box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
            }}
            .card:hover {{
              transform: translateY(-1px);
              border-color: rgba(139, 61, 255, 0.42);
              background: linear-gradient(180deg, rgba(50, 54, 66, 0.96), rgba(32, 35, 44, 0.98));
            }}
            .card-title {{
              font-size: 16px;
              font-weight: 600;
              line-height: 1.4;
            }}
            .card-url {{
              margin-top: 8px;
              color: #8ec5ff;
              font-size: 13px;
              word-break: break-all;
            }}
            .card-meta {{
              margin-top: 10px;
              color: var(--muted);
              font-size: 12px;
            }}
            .empty {{
              padding: 34px;
              border: 1px dashed var(--border);
              border-radius: 24px;
              background: rgba(255, 255, 255, 0.03);
              color: var(--muted);
              text-align: center;
            }}
          </style>
        </head>
        <body>
          <main class="page">
            <section class="hero">
              <div class="eyebrow">Research Browser</div>
              <h1>{escape(title)}</h1>
              <div class="subtitle">{escape(subtitle)}</div>
            </section>
            <section class="list">
              {items_html}
            </section>
          </main>
        </body>
        </html>
        """

    def toggle_pin_current_tab(self, force_pin: Optional[bool] = None) -> str:
        tab = self.current_browser_tab()
        if tab is None:
            return "There is no active tab to pin."
        current_index = self.tabs.currentIndex()
        should_pin = not tab.is_pinned if force_pin is None else force_pin
        tab.is_pinned = should_pin
        self.tabs.removeTab(current_index)
        new_index = self._pinned_insert_index() if should_pin else self.tabs.count()
        self.tabs.insertTab(new_index, tab, self._display_title(tab.title(), should_pin))
        self.tabs.setCurrentWidget(tab)
        self._sync_chrome()
        return "Pinned the current tab." if should_pin else "Unpinned the current tab."

    def _pinned_insert_index(self) -> int:
        count = 0
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if getattr(tab, "is_pinned", False):
                count += 1
        return count

    def _display_title(self, title: str, pinned: bool) -> str:
        safe_title = title or "New Tab"
        return safe_title[:14] if pinned else safe_title[:28]

    def _update_tab_title(self, tab: BrowserTab, title: str) -> None:
        index = self.tabs.indexOf(tab)
        if index >= 0:
            self.tabs.setTabText(index, self._display_title(title, tab.is_pinned))
            self._sync_chrome()

    def _update_tab_url(self, tab: BrowserTab, qurl: QUrl) -> None:
        if tab is self.current_browser_tab():
            self.browser_chrome.set_url(qurl.toString())
            self._sync_bookmark_state()
        self._update_tab_title(tab, tab.title())
        self._sync_chrome()

    def _current_tab_changed(self, index: int) -> None:
        tab = self.tabs.widget(index)
        if isinstance(tab, BrowserTab):
            self.browser_chrome.set_url(tab.url().toString())
        self._sync_bookmark_state()
        self._sync_chrome()

    def get_tab_descriptions(self) -> List[str]:
        descriptions = []
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if isinstance(tab, BrowserTab):
                prefix = "[Pinned] " if tab.is_pinned else ""
                descriptions.append(f"{index}: {prefix}{tab.title() or 'New Tab'}")
        return descriptions

    def _submit_chat_message(self, message: str) -> None:
        self.chat_panel.add_message("user", message)
        self.agent_controller.handle_message(message)

    def _handle_quick_action(self, prompt: str) -> None:
        if prompt.endswith("for "):
            query, accepted = QInputDialog.getText(self, "Search Scholar", "Enter research topic:")
            if not accepted or not query.strip():
                return
            prompt = f"{prompt}{query.strip()}"
        self._submit_chat_message(prompt)

    def _show_agent_error(self, error_text: str) -> None:
        self.chat_panel.add_message("assistant", f"I hit an error: {error_text}")

    def toggle_proxy_mode(self) -> None:
        new_enabled = not self.proxy_settings.get("proxy_enabled", False)
        self.settings["proxy_enabled"] = new_enabled
        self.proxy_settings = self._settings_with_env_overrides(forced_enabled=new_enabled)
        self.proxy_manager = ProxyManager(self.proxy_settings)
        self.proxy_manager.apply()
        self.browser_chrome.set_proxy_state(new_enabled)
        self.settings_manager.save(self.settings)
        self.statusBar().showMessage(
            "PSTU proxy enabled. Reload pages if needed." if new_enabled else "Direct mode enabled.",
            4000,
        )

    def _restore_window(self) -> None:
        self.resize(self.settings["window_width"], self.settings["window_height"])

    def _restore_session(self) -> None:
        session = self.session_manager.load()
        for tab_info in session.get("tabs", []):
            self.add_new_tab(
                url=tab_info.get("url") or self.settings["homepage"],
                make_current=False,
                pinned=tab_info.get("pinned", False),
            )
        if self.tabs.count() and session.get("current_index", 0) < self.tabs.count():
            self.tabs.setCurrentIndex(session.get("current_index", 0))
        self._sync_chrome()

    def _handle_load_progress(self, tab: BrowserTab, progress: int) -> None:
        self.statusBar().showMessage(f"Loading... {progress}%")
        if tab is self.current_browser_tab():
            self.browser_chrome.set_loading(progress)

    def _handle_load_finished(self, tab: BrowserTab, ok: bool) -> None:
        self.statusBar().showMessage("Ready" if ok else "Failed to load page")
        if ok:
            self.history_manager.add(tab.title() or tab.url().toString(), tab.url().toString())

    def _sync_chrome(self) -> None:
        tabs = []
        current = self.tabs.currentIndex()
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if isinstance(tab, BrowserTab):
                tabs.append(
                    {
                        "title": tab.title() or "New Tab",
                        "url": tab.url().toString(),
                        "pinned": tab.is_pinned,
                        "active": index == current,
                    }
                )
        self.browser_chrome.set_tabs(tabs)
        current_tab = self.current_browser_tab()
        if current_tab:
            self.browser_chrome.set_url(current_tab.url().toString())
        self._sync_bookmark_state()

    def _sync_bookmark_state(self) -> None:
        current_tab = self.current_browser_tab()
        current_url = current_tab.url().toString() if current_tab else ""
        self.browser_chrome.set_bookmark_state(self.bookmark_manager.contains(current_url))

    def _set_current_tab(self, index: int) -> None:
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def open_bookmark_picker(self) -> None:
        bookmarks = self.bookmark_manager.load()
        items = [
            {
                "title": item.get("title") or item.get("url", "Untitled"),
                "url": item.get("url", ""),
                "meta": "Saved bookmark",
            }
            for item in bookmarks
        ]
        html = self._build_library_page(
            "Bookmarks",
            "Open saved papers, articles, and research sources from a cleaner in-browser library view.",
            items,
            "No bookmarks saved yet.",
        )
        self._open_library_tab("Bookmarks", html)

    def open_history_picker(self) -> None:
        history = self.history_manager.load()
        items = [
            {
                "title": item.get("title") or item.get("url", "Untitled"),
                "url": item.get("url", ""),
                "meta": item.get("visited_at", ""),
            }
            for item in history[:100]
        ]
        html = self._build_library_page(
            "History",
            "Review recent browsing activity and reopen pages directly from this tab.",
            items,
            "No browsing history yet.",
        )
        self._open_library_tab("History", html)

    def closeEvent(self, event) -> None:
        self.settings["window_width"] = self.width()
        self.settings["window_height"] = self.height()
        self.settings_manager.save(self.settings)

        tabs = []
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if isinstance(tab, BrowserTab):
                url = tab.url().toString()
                if url:
                    tabs.append({"url": url, "pinned": tab.is_pinned})
        self.session_manager.save({"tabs": tabs, "current_index": self.tabs.currentIndex()})
        super().closeEvent(event)


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Researcher")
    window = BrowserWindow()
    window.show()
    sys.exit(app.exec())
