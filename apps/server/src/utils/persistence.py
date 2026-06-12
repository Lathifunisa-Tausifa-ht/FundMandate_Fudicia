from __future__ import annotations
import json
from pathlib import Path
from typing import Any

LOG_DIR = Path("logs")

def dump_json(data: Any, name: str) -> None:
    """write `data` as pretty JSON to `logs/<name>`."""
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    path = LOG_DIR / name
    with open(path, "w", encoding="utf‑8") as f:
        json.dump(data, f, indent=2)

def dump_text(text: str, name: str) -> None:
    LOG_DIR.mkdir(exist_ok=True, parents=True)
    with open(LOG_DIR / name, "w", encoding="utf‑8") as f:
        f.write(text)