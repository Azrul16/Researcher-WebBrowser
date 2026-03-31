from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests

SOCIAL_MEDIA_DOMAINS: set[str] = set()
ADULT_DOMAINS: set[str] = set()
ADULT_KEYWORDS: set[str] = set()
BLOCKLIST_URL = ""
_downloaded_domains: set[str] = set()
_loaded = False


def classify_url(url: str) -> str | None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return None

    if _matches_domain(hostname, SOCIAL_MEDIA_DOMAINS):
        return "social media"

    if _matches_domain(hostname, ADULT_DOMAINS):
        return "adult content"

    lowered = url.lower()
    if any(keyword in hostname or keyword in lowered for keyword in ADULT_KEYWORDS):
        return "adult content"

    if _matches_domain(hostname, _downloaded_domains):
        return "blocked content"

    return None


def is_blocked_url(url: str) -> bool:
    return classify_url(url) is not None


def _matches_domain(hostname: str, domains: set[str]) -> bool:
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains)


def initialize_blocklists(cache_path: Path) -> None:
    global _loaded, _downloaded_domains, SOCIAL_MEDIA_DOMAINS, ADULT_DOMAINS, ADULT_KEYWORDS, BLOCKLIST_URL
    if _loaded:
        return

    SOCIAL_MEDIA_DOMAINS = _parse_env_set("BLOCKED_SOCIAL_DOMAINS")
    ADULT_DOMAINS = _parse_env_set("BLOCKED_ADULT_DOMAINS")
    ADULT_KEYWORDS = _parse_env_set("BLOCKED_ADULT_KEYWORDS")
    BLOCKLIST_URL = os.getenv(
        "BLOCKLIST_SOURCE_URL",
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn-social-only/hosts",
    ).strip()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    domains = _load_from_cache(cache_path)
    if not domains:
        domains = _fetch_domains()
        if domains:
            cache_path.write_text(json.dumps(sorted(domains)), encoding="utf-8")

    _downloaded_domains = domains
    _loaded = True


def _load_from_cache(cache_path: Path) -> set[str]:
    if not cache_path.exists():
        return set()
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {item.strip().lower() for item in payload if isinstance(item, str) and item.strip()}


def _fetch_domains() -> set[str]:
    if not BLOCKLIST_URL:
        return set()
    try:
        response = requests.get(BLOCKLIST_URL, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return set()

    domains: set[str] = set()
    for raw_line in response.text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] in {"0.0.0.0", "127.0.0.1"}:
            hostname = parts[1].strip().lower()
            if hostname and hostname != "localhost":
                domains.add(hostname)
    return domains


def _parse_env_set(name: str) -> set[str]:
    value = os.getenv(name, "")
    if not value.strip():
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}
