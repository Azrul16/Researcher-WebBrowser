from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from PyQt6.QtNetwork import QNetworkProxy


class ProxyManager:
    def __init__(self, settings: Dict):
        self.settings = settings

    def apply(self) -> None:
        if not self.settings.get("proxy_enabled"):
            QNetworkProxy.setApplicationProxy(QNetworkProxy())
            return

        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.ProxyType.HttpProxy)
        proxy.setHostName(self.settings.get("proxy_host", ""))
        proxy.setPort(int(self.settings.get("proxy_port", 8080)))
        proxy.setUser(self.settings.get("proxy_username", ""))
        proxy.setPassword(self.settings.get("proxy_password", ""))
        QNetworkProxy.setApplicationProxy(proxy)

    @staticmethod
    def load_foxyproxy_settings(config_path: Path) -> Dict:
        payload = ProxyManager._read_foxyproxy_payload(config_path)
        if not payload:
            return {}

        mode = str(payload.get("mode", "")).strip().lower()
        if mode in {"disable", "disabled", "off", "none"}:
            return {"proxy_enabled": False}

        return ProxyManager._extract_active_proxy(payload, include_enabled=True)

    @staticmethod
    def load_foxyproxy_profile(config_path: Path) -> Dict:
        payload = ProxyManager._read_foxyproxy_payload(config_path)
        if not payload:
            return {}
        return ProxyManager._extract_active_proxy(payload, include_enabled=False)

    @staticmethod
    def _read_foxyproxy_payload(config_path: Path) -> Dict:
        if not config_path.exists():
            return {}

        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _extract_active_proxy(payload: Dict, include_enabled: bool) -> Dict:
        proxies = payload.get("data", [])
        active_proxy = next((item for item in proxies if item.get("active")), None)
        if not active_proxy:
            return {}

        profile = {
            "proxy_host": active_proxy.get("hostname", ""),
            "proxy_port": int(active_proxy.get("port", 8080)),
            "proxy_username": active_proxy.get("username", ""),
            "proxy_password": active_proxy.get("password", ""),
        }
        if include_enabled:
            profile["proxy_enabled"] = True
        return profile
