"""녹화 영상 입력(--video) 테스트 — 웹캠 없이 엔진 루프가 영상을 끝까지 처리하는지."""

import time

import cv2
import numpy as np

from kiosk.config import load_config
from kiosk.detector import MockDetector
from kiosk.engine import KioskEngine


def test_영상파일을_웹캠대신_재생(tmp_path):
    path = tmp_path / "clip.mp4"
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (64, 48))
    for _ in range(15):  # 0.5초
        out.write(np.zeros((48, 64, 3), np.uint8))
    out.release()

    cfg = load_config()
    cfg["camera"].update({"enabled": True, "video": str(path), "loop": False})
    cfg["log_events"] = False
    eng = KioskEngine(cfg, detector=MockDetector([("palm", (0.4, 0.4, 0.6, 0.6))]))
    eng.start()
    deadline = time.monotonic() + 5
    while eng._thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    eng.stop()
    assert eng.camera_ok
    assert eng.frames == 15                    # 모든 프레임 처리, 반복 안 함
    assert eng.latest_jpeg() is not None        # 미리보기 생성
