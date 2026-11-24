"""설정 파일(configs/app.yaml) 읽기."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .gestures import GestureConfig

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "configs" / "app.yaml"


def load_config(path: str | Path | None = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("camera", {})
    cfg.setdefault("detector", {"backend": "mock"})
    cfg.setdefault("gesture", {})
    cfg.setdefault("server", {})
    # 상대 경로는 저장소 루트 기준으로
    mp = cfg["detector"].get("model_path")
    if mp and not Path(mp).is_absolute():
        cfg["detector"]["model_path"] = str(ROOT / mp)
    return cfg


def gesture_config(cfg: Dict[str, Any]) -> GestureConfig:
    g = dict(cfg.get("gesture") or {})
    for key in ("active_region", "pointer_labels", "grab_labels", "swipe_labels"):
        if key in g:
            g[key] = tuple(g[key])
    return GestureConfig(**g)
