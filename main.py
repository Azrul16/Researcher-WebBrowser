from pathlib import Path

from app_paths import app_base_dir
from browser_window import run


def load_local_env() -> None:
    candidates = [
        app_base_dir() / ".env.local",
        Path.cwd() / ".env.local",
    ]

    for env_path in candidates:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                import os

                os.environ.setdefault(key, value)


if __name__ == "__main__":
    load_local_env()
    run()
