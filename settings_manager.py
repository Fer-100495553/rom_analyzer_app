from __future__ import annotations

import json
import os

_PATH = os.path.join(os.path.dirname(__file__), ".settings.json")
_DEFAULTS: dict[str, str] = {"language": "en", "theme": "System"}
_data: dict[str, str] = {}


def _load() -> None:
    global _data
    try:
        with open(_PATH, encoding="utf-8") as f:
            _data = {**_DEFAULTS, **json.load(f)}
    except Exception:
        _data = dict(_DEFAULTS)


def _save() -> None:
    try:
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2)
    except Exception:
        pass


def get(key: str) -> str:
    return _data.get(key, _DEFAULTS.get(key, ""))


def set_language(lang: str) -> None:
    _data["language"] = lang
    _save()


def set_theme(theme: str) -> None:
    _data["theme"] = theme
    _save()


_load()
