"""카메라 → 탐지 → 제스처 해석 → 이벤트 전달을 반복하는 백그라운드 엔진.

웹서버(server.py)와는 콜백 하나(on_event)로만 연결됩니다.
엔진은 별도 스레드에서 돌고, 서버는 asyncio 이벤트 루프에서 돌기 때문에
서버 쪽 콜백은 loop.call_soon_threadsafe 로 넘겨받습니다.
"""

from __future__ import annotations

import csv
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

import numpy as np

from .config import ROOT, gesture_config
from .detector import BaseDetector, build_detector
from .gestures import Detection, GestureInterpreter

EventCallback = Callable[[dict], None]

# 미리보기 박스 색 (BGR)
_COLORS = {"one": (255, 170, 0), "fist": (0, 0, 255), "palm": (0, 200, 0),
           "like": (0, 215, 255), "dislike": (180, 0, 180), "peace": (255, 0, 255)}


class KioskEngine:
    def __init__(self, cfg: dict, detector: Optional[BaseDetector] = None) -> None:
        self.cfg = cfg
        self.detector = detector or build_detector(cfg["detector"])
        self.interpreter = GestureInterpreter(gesture_config(cfg))
        self.on_event: Optional[EventCallback] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._jpeg: Optional[bytes] = None
        self._jpeg_lock = threading.Lock()
        self.fps = 0.0
        self.latency_ms = 0.0
        self.frames = 0
        self.camera_ok = False
        self.last_detections: List[Detection] = []
        self._log_writer = None
        self._log_file = None

    # ------------------------------------------------------------------ 상태
    def status(self) -> dict:
        return {
            "type": "status",
            "backend": self.detector.name,
            "camera": self.camera_ok,
            "fps": round(self.fps, 1),
            "latency_ms": round(self.latency_ms, 1),
            "frames": self.frames,
            "gesture": self.interpreter.stable_gesture,
            "hands": len(self.last_detections),
        }

    def latest_jpeg(self) -> Optional[bytes]:
        with self._jpeg_lock:
            return self._jpeg

    # ------------------------------------------------------------------ 시작/정지
    def start(self) -> None:
        if not self.cfg["camera"].get("enabled", True):
            print("[엔진] camera.enabled=false → 카메라 없이 실행 (화면은 키보드·마우스로 조작)")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="kiosk-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._log_file:
            self._log_file.close()

    # ------------------------------------------------------------------ 처리 1프레임
    def process_frame(self, frame_bgr: np.ndarray, t: Optional[float] = None) -> List[dict]:
        """프레임 1장 처리. 테스트·녹화영상 평가에서도 직접 호출 가능."""
        t = time.monotonic() if t is None else t
        dets, ms = self.detector.timed_detect(frame_bgr)
        self.last_detections = dets
        self.latency_ms = ms if self.frames == 0 else 0.9 * self.latency_ms + 0.1 * ms
        self.frames += 1
        events = [e.to_dict() for e in self.interpreter.update(dets, t)]
        for e in events:
            self._log(e, ms)
            if self.on_event:
                self.on_event(e)
        return events

    def _loop(self) -> None:
        import cv2

        cam = self.cfg["camera"]
        video = cam.get("video")  # 녹화 영상 파일 (웹캠 대신) — 재현 가능한 테스트·시연 백업용
        if video:
            cap = cv2.VideoCapture(str(video))
            frame_dt = 1.0 / (cap.get(cv2.CAP_PROP_FPS) or 30.0)
            source = f"영상 {video}"
        else:
            cap = cv2.VideoCapture(cam.get("index", 0))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam.get("width", 1280))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam.get("height", 720))
            frame_dt = 0.0
            source = f"카메라 {cam.get('index', 0)}"
        self.camera_ok = cap.isOpened()
        if not self.camera_ok:
            what = "camera.video 경로" if video else "camera.index"
            print(f"[엔진] ⚠️ {source} 을(를) 열 수 없습니다. {what} 를 확인하세요."
                  " 키보드·마우스 모드로 계속합니다.")
            return
        print(f"[엔진] {source} 시작, 탐지기 = {self.detector.name}")
        last_status = 0.0
        prev = time.monotonic()
        next_due = prev
        while self._running:
            if frame_dt:  # 영상은 원래 속도로 재생 (제스처 판정이 시간 기준이므로)
                wait = next_due - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                next_due = max(next_due + frame_dt, time.monotonic() - frame_dt)
            ok, frame = cap.read()
            if not ok:
                if video and cam.get("loop", True):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 끝나면 처음부터 반복
                    continue
                if video:
                    print("[엔진] 영상 재생 끝")
                    break
                time.sleep(0.01)
                continue
            now = time.monotonic()
            dt = now - prev
            prev = now
            if dt > 0:
                self.fps = 1 / dt if self.fps == 0 else 0.9 * self.fps + 0.1 / dt
            self.process_frame(frame, now)
            self._update_preview(frame)
            if now - last_status > 0.5 and self.on_event:
                self.on_event(self.status())
                last_status = now
        cap.release()

    # ------------------------------------------------------------------ 미리보기·로그
    def _update_preview(self, frame: np.ndarray) -> None:
        import cv2

        h, w = frame.shape[:2]
        vis = frame.copy()
        for d in self.last_detections:
            x1, y1, x2, y2 = (int(d.box[0] * w), int(d.box[1] * h),
                              int(d.box[2] * w), int(d.box[3] * h))
            color = _COLORS.get(d.label, (200, 200, 200))
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 3)
        if self.cfg["gesture"].get("mirror", True):
            vis = cv2.flip(vis, 1)
        # 글자는 반전 후에 써야 거꾸로 안 보임
        for d in self.last_detections:
            x1 = int((1 - d.box[2]) * w) if self.cfg["gesture"].get("mirror", True) \
                else int(d.box[0] * w)
            y1 = int(d.box[1] * h)
            cv2.putText(vis, f"{d.label} {d.conf:.2f}", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, _COLORS.get(d.label, (200, 200, 200)), 2)
        cv2.putText(vis, f"FPS {self.fps:.1f} | {self.latency_ms:.0f} ms", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        vis = cv2.resize(vis, (w * 360 // h, 360))
        ok, buf = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            with self._jpeg_lock:
                self._jpeg = buf.tobytes()

    def _log(self, event: dict, ms: float) -> None:
        """명령 이벤트를 CSV로 기록 → 성능평가(명령 인식률·지연) 자료."""
        if not self.cfg.get("log_events", True) or event["type"] in ("cursor", "hold"):
            return
        if self._log_writer is None:
            d = ROOT / "logs"
            d.mkdir(exist_ok=True)
            path = d / f"events_{datetime.now():%Y%m%d_%H%M%S}.csv"
            self._log_file = open(path, "w", newline="", encoding="utf-8")
            self._log_writer = csv.writer(self._log_file)
            self._log_writer.writerow(["time", "type", "gesture", "direction", "detect_ms"])
        self._log_writer.writerow([f"{time.time():.3f}", event["type"], event.get("gesture", ""),
                                   event.get("direction", ""), f"{ms:.1f}"])
        self._log_file.flush()
