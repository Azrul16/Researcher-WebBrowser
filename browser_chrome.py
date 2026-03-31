from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class BrowserChromeBridge(QObject):
    backRequested = pyqtSignal()
    forwardRequested = pyqtSignal()
    reloadRequested = pyqtSignal()
    homeRequested = pyqtSignal()
    newTabRequested = pyqtSignal()
    openHistoryRequested = pyqtSignal()
    openBookmarksRequested = pyqtSignal()
    addBookmarkRequested = pyqtSignal()
    navigateRequested = pyqtSignal(str)
    proxyToggleRequested = pyqtSignal()
    tabSelected = pyqtSignal(int)
    tabClosed = pyqtSignal(int)

    @pyqtSlot()
    def goBack(self) -> None:
        self.backRequested.emit()

    @pyqtSlot()
    def goForward(self) -> None:
        self.forwardRequested.emit()

    @pyqtSlot()
    def reload(self) -> None:
        self.reloadRequested.emit()

    @pyqtSlot()
    def goHome(self) -> None:
        self.homeRequested.emit()

    @pyqtSlot()
    def newTab(self) -> None:
        self.newTabRequested.emit()

    @pyqtSlot()
    def openHistory(self) -> None:
        self.openHistoryRequested.emit()

    @pyqtSlot()
    def openBookmarks(self) -> None:
        self.openBookmarksRequested.emit()

    @pyqtSlot()
    def addBookmark(self) -> None:
        self.addBookmarkRequested.emit()

    @pyqtSlot(str)
    def navigate(self, value: str) -> None:
        self.navigateRequested.emit(value)

    @pyqtSlot()
    def toggleProxy(self) -> None:
        self.proxyToggleRequested.emit()

    @pyqtSlot(int)
    def selectTab(self, index: int) -> None:
        self.tabSelected.emit(index)

    @pyqtSlot(int)
    def closeTab(self, index: int) -> None:
        self.tabClosed.emit(index)


class BrowserChrome(QWebEngineView):
    back_requested = pyqtSignal()
    forward_requested = pyqtSignal()
    reload_requested = pyqtSignal()
    home_requested = pyqtSignal()
    new_tab_requested = pyqtSignal()
    open_history_requested = pyqtSignal()
    open_bookmarks_requested = pyqtSignal()
    add_bookmark_requested = pyqtSignal()
    navigate_requested = pyqtSignal(str)
    proxy_toggle_requested = pyqtSignal()
    tab_selected = pyqtSignal(int)
    tab_closed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loaded = False
        self._pending_scripts: list[str] = []

        self.bridge = BrowserChromeBridge()
        self.bridge.backRequested.connect(self.back_requested.emit)
        self.bridge.forwardRequested.connect(self.forward_requested.emit)
        self.bridge.reloadRequested.connect(self.reload_requested.emit)
        self.bridge.homeRequested.connect(self.home_requested.emit)
        self.bridge.newTabRequested.connect(self.new_tab_requested.emit)
        self.bridge.openHistoryRequested.connect(self.open_history_requested.emit)
        self.bridge.openBookmarksRequested.connect(self.open_bookmarks_requested.emit)
        self.bridge.addBookmarkRequested.connect(self.add_bookmark_requested.emit)
        self.bridge.navigateRequested.connect(self.navigate_requested.emit)
        self.bridge.proxyToggleRequested.connect(self.proxy_toggle_requested.emit)
        self.bridge.tabSelected.connect(self.tab_selected.emit)
        self.bridge.tabClosed.connect(self.tab_closed.emit)

        channel = QWebChannel(self.page())
        channel.registerObject("browserBridge", self.bridge)
        self.page().setWebChannel(channel)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setMaximumHeight(112)
        self.loadFinished.connect(self._on_load_finished)
        self._load_ui()

    def _load_ui(self) -> None:
        html = (ASSETS_DIR / "browser_chrome.html").read_text(encoding="utf-8")
        self.setHtml(html, QUrl.fromLocalFile(str(ASSETS_DIR) + "/"))

    def _on_load_finished(self, ok: bool) -> None:
        self._loaded = ok
        if not ok:
            return
        while self._pending_scripts:
            self.page().runJavaScript(self._pending_scripts.pop(0))

    def _run(self, script: str) -> None:
        if self._loaded:
            self.page().runJavaScript(script)
        else:
            self._pending_scripts.append(script)

    def set_tabs(self, tabs: list[dict]) -> None:
        self._run(f"window.browserChrome.setTabs({json.dumps(tabs)});")

    def set_url(self, url: str) -> None:
        self._run(f"window.browserChrome.setUrl({json.dumps(url)});")

    def set_loading(self, progress: int) -> None:
        self._run(f"window.browserChrome.setLoading({int(progress)});")

    def set_proxy_state(self, enabled: bool) -> None:
        self._run(f"window.browserChrome.setProxyState({json.dumps(bool(enabled))});")

    def set_bookmark_state(self, bookmarked: bool) -> None:
        self._run(f"window.browserChrome.setBookmarkState({json.dumps(bool(bookmarked))});")
