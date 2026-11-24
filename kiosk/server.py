"""FastAPI 웹서버 — 키오스크 화면(web/) 제공 + WebSocket 으로 제스처 이벤트 전달.

엔드포인트
    GET  /                 키오스크 화면 (web/index.html)
    GET  /api/content      안내 콘텐츠 JSON (web/content/kiosk_content.json)
    GET  /api/status       엔진 상태 (FPS, 지연시간, 탐지기 종류)
    GET  /video            카메라 미리보기 (MJPEG, 박스 표시)
    WS   /ws               이벤트 스트림 (cursor / click / swipe / confirm / back / home ...)
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT
from .engine import KioskEngine

WEB_DIR = ROOT / "web"


def create_app(cfg: dict, engine: Optional[KioskEngine] = None) -> FastAPI:
    engine = engine or KioskEngine(cfg)
    clients: Set[WebSocket] = set()
    state: dict = {"loop": None}

    async def broadcast(event: dict) -> None:
        dead = []
        msg = json.dumps(event, ensure_ascii=False)
        for ws in list(clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

    def on_event(event: dict) -> None:
        # 엔진 스레드 → asyncio 루프로 안전하게 넘김
        loop = state["loop"]
        if loop is not None:
            loop.call_soon_threadsafe(lambda: asyncio.ensure_future(broadcast(event)))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state["loop"] = asyncio.get_running_loop()
        engine.on_event = on_event
        engine.start()
        yield
        engine.stop()

    app = FastAPI(title="모션인식 탐색 키오스크", lifespan=lifespan)
    app.state.engine = engine

    @app.get("/api/status")
    def api_status():
        return engine.status()

    @app.get("/api/content")
    def api_content():
        with open(WEB_DIR / "content" / "kiosk_content.json", encoding="utf-8") as f:
            return JSONResponse(json.load(f))

    @app.get("/video")
    async def video():
        async def gen():
            while True:
                jpg = engine.latest_jpeg()
                if jpg:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
                await asyncio.sleep(1 / 15)

        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        clients.add(ws)
        await ws.send_text(json.dumps(engine.status(), ensure_ascii=False))
        try:
            while True:
                await ws.receive_text()  # 화면 → 서버 메시지는 현재 사용 안 함 (연결 유지용)
        except WebSocketDisconnect:
            clients.discard(ws)

    # 정적 파일은 맨 마지막에 마운트 (위 경로들이 먼저 매칭되도록)
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
