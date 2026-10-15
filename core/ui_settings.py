import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
MIN_SCALE = 0.8
MAX_SCALE = 1.6


def load_ui_scale() -> float:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return min(MAX_SCALE, max(MIN_SCALE, float(data.get("ui_scale", 1.0))))
    except (OSError, ValueError, TypeError, AttributeError):
        return 1.0


def save_ui_scale(value: float) -> None:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data["ui_scale"] = round(min(MAX_SCALE, max(MIN_SCALE, value)), 2)
    CONFIG_PATH.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
