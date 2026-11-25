"""실행: python -m kiosk [--config configs/app.yaml] [--mock] [--port 8000]

--mock : 카메라·모델 없이 실행 (화면은 키보드·마우스로 조작) — 화면 개발용
"""

from __future__ import annotations

import argparse
import webbrowser

import uvicorn

from .config import load_config
from .server import create_app


def main() -> None:
    ap = argparse.ArgumentParser(description="모션인식 탐색 키오스크 실행")
    ap.add_argument("--config", default=None, help="설정 파일 (기본 configs/app.yaml)")
    ap.add_argument("--mock", action="store_true", help="카메라·모델 없이 실행")
    ap.add_argument("--backend", choices=["mock", "yolo", "rfdetr"], help="탐지기 강제 지정")
    ap.add_argument("--model", help="모델 가중치 경로 (configs 값 대신)")
    ap.add_argument("--camera", type=int, help="카메라 번호 (기본 0)")
    ap.add_argument("--video", help="웹캠 대신 녹화 영상 파일로 실행 (테스트·시연 백업)")
    ap.add_argument("--no-loop", action="store_true", help="--video 를 한 번만 재생")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--no-browser", action="store_true", help="브라우저 자동 실행 안 함")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.mock:
        cfg["detector"]["backend"] = "mock"
        cfg["camera"]["enabled"] = False
    if args.backend:
        cfg["detector"]["backend"] = args.backend
    if args.model:
        cfg["detector"]["model_path"] = args.model
    if args.camera is not None:
        cfg["camera"]["index"] = args.camera
    if args.video:
        cfg["camera"]["video"] = args.video
        cfg["camera"]["enabled"] = True
        cfg["camera"]["loop"] = not args.no_loop

    host = cfg["server"].get("host", "127.0.0.1")
    port = args.port or cfg["server"].get("port", 8000)
    url = f"http://{host}:{port}"
    print(f"[키오스크] {url} 에서 실행합니다. (탐지기: {cfg['detector']['backend']})")
    if not args.no_browser:
        webbrowser.open(url)
    uvicorn.run(create_app(cfg), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
