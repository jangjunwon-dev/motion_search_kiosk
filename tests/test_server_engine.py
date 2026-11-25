"""엔진·서버 통합 테스트 — mock 탐지기로 프레임 → 이벤트 → WebSocket 흐름 확인."""

import numpy as np
from fastapi.testclient import TestClient

from kiosk.config import load_config
from kiosk.detector import MockDetector
from kiosk.engine import KioskEngine
from kiosk.server import create_app

BOX = (0.4, 0.4, 0.6, 0.6)


def mock_cfg():
    cfg = load_config()
    cfg["detector"]["backend"] = "mock"
    cfg["camera"]["enabled"] = False
    cfg["log_events"] = False
    return cfg


def test_엔진_프레임처리_클릭까지():
    script = [("one", BOX)] * 8 + [("fist", BOX)] * 4
    eng = KioskEngine(mock_cfg(), detector=MockDetector(script))
    frame = np.zeros((480, 640, 3), np.uint8)
    got = []
    for i in range(len(script)):
        got += eng.process_frame(frame, t=i / 30)
    kinds = [e["type"] for e in got]
    assert "cursor" in kinds and "click" in kinds
    assert eng.status()["frames"] == len(script)


def test_서버_화면과_API():
    app = create_app(mock_cfg())
    with TestClient(app) as c:
        assert "모션인식" in c.get("/").text
        content = c.get("/api/content").json()
        assert len(content["categories"]) >= 3
        st = c.get("/api/status").json()
        assert st["backend"] == "mock" and st["camera"] is False


def test_웹소켓_이벤트_전달():
    eng = KioskEngine(mock_cfg(), detector=MockDetector([("like", BOX)]))
    app = create_app(mock_cfg(), engine=eng)
    frame = np.zeros((120, 160, 3), np.uint8)
    with TestClient(app) as c:
        with c.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["type"] == "status"
            for i in range(30):
                eng.process_frame(frame, t=i / 30)
            seen = set()
            for _ in range(40):
                seen.add(ws.receive_json()["type"])
                if "confirm" in seen:
                    break
            assert "confirm" in seen


def test_사용중인_포트는_다음번호로():
    import socket

    from kiosk.__main__ import pick_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        used = busy.getsockname()[1]
        got = pick_port("127.0.0.1", used)
        assert got != used and used < got < used + 10
