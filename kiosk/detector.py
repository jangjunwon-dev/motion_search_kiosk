"""손동작 객체탐지기 — YOLO(Ultralytics) / RF-DETR / mock 백엔드를 같은 인터페이스로 감쌈.

모든 탐지기는 detect(frame_bgr) → List[Detection] 을 제공합니다.
좌표는 0~1 정규화 (x1, y1, x2, y2) 로 통일
→ 카메라 해상도가 달라도 gestures.py 가 그대로 동작합니다.

무거운 라이브러리(torch, ultralytics, rfdetr)는 실제로 그 백엔드를 쓸 때만 import 합니다.
→ mock 모드와 테스트는 GPU·모델 없이도 실행됩니다.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from .gestures import Detection


class BaseDetector:
    name = "base"

    def detect(self, frame_bgr: np.ndarray) -> List[Detection]:  # pragma: no cover
        raise NotImplementedError

    def timed_detect(self, frame_bgr: np.ndarray) -> tuple[List[Detection], float]:
        """탐지 + 소요 시간(ms). 성능평가(지연시간) 기록에 사용."""
        t0 = time.perf_counter()
        dets = self.detect(frame_bgr)
        return dets, (time.perf_counter() - t0) * 1000.0


class MockDetector(BaseDetector):
    """모델 없이 개발할 때 쓰는 가짜 탐지기.

    script 가 주어지면 [(label, box), ...] 를 프레임마다 순서대로 돌려주고, 없으면 빈 결과.
    화면 쪽은 키보드·마우스로 같은 이벤트를 흉내낼 수 있으므로(web/app.js)
    보통은 빈 결과로 충분합니다.
    """

    name = "mock"

    def __init__(self, script: Optional[Sequence[Optional[tuple]]] = None) -> None:
        self.script = list(script or [])
        self.i = 0

    def detect(self, frame_bgr: np.ndarray) -> List[Detection]:
        if not self.script:
            return []
        item = self.script[self.i % len(self.script)]
        self.i += 1
        if item is None:
            return []
        label, box = item
        return [Detection(label, 0.9, tuple(box))]


class YoloDetector(BaseDetector):
    """Ultralytics YOLO (YOLO26 / YOLO11 / YOLOv13 등 .pt 가중치)."""

    name = "yolo"

    def __init__(self, model_path: str, conf: float = 0.4, imgsz: int = 640,
                 device: Optional[str] = None,
                 label_map: Optional[Dict[str, str]] = None) -> None:
        from ultralytics import YOLO  # 지연 import

        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"모델 파일이 없습니다: {model_path}\n"
                "→ 공유 드라이브 models/ 에서 받아 저장소 models/ 폴더에 넣으세요."
                " (models/README.md)")
        self.model = YOLO(model_path)
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        self.label_map = label_map or {}

    def detect(self, frame_bgr: np.ndarray) -> List[Detection]:
        h, w = frame_bgr.shape[:2]
        res = self.model.predict(frame_bgr, conf=self.conf, imgsz=self.imgsz,
                                 device=self.device, verbose=False)[0]
        names = res.names
        out: List[Detection] = []
        if res.boxes is None:
            return out
        for xyxy, c, k in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.conf.cpu().numpy(),
                              res.boxes.cls.cpu().numpy().astype(int)):
            label = names[int(k)]
            label = self.label_map.get(label, label)
            x1, y1, x2, y2 = xyxy
            out.append(Detection(label, float(c), (x1 / w, y1 / h, x2 / w, y2 / h)))
        return out


class RFDetrDetector(BaseDetector):
    """Roboflow RF-DETR (DETR 계열 실시간 탐지기, NMS 없음)."""

    name = "rfdetr"

    def __init__(self, model_path: str, class_names: Sequence[str], conf: float = 0.4,
                 size: str = "base", label_map: Optional[Dict[str, str]] = None) -> None:
        import rfdetr  # 지연 import

        cls = {"nano": "RFDETRNano", "small": "RFDETRSmall", "base": "RFDETRBase",
               "medium": "RFDETRMedium"}.get(size, "RFDETRBase")
        self.model = getattr(rfdetr, cls)(pretrain_weights=model_path)
        try:
            self.model.optimize_for_inference()
        except Exception:  # 버전에 따라 없을 수 있음
            pass
        self.class_names = list(class_names)
        self.conf = conf
        self.label_map = label_map or {}

    def detect(self, frame_bgr: np.ndarray) -> List[Detection]:
        h, w = frame_bgr.shape[:2]
        rgb = frame_bgr[:, :, ::-1].copy()
        dets = self.model.predict(rgb, threshold=self.conf)
        out: List[Detection] = []
        for xyxy, c, k in zip(dets.xyxy, dets.confidence, dets.class_id):
            k = int(k)
            label = self.class_names[k] if 0 <= k < len(self.class_names) else str(k)
            label = self.label_map.get(label, label)
            x1, y1, x2, y2 = xyxy
            out.append(Detection(label, float(c), (x1 / w, y1 / h, x2 / w, y2 / h)))
        return out


def build_detector(cfg: dict) -> BaseDetector:
    """configs/app.yaml 의 detector 항목으로 탐지기 생성."""
    backend = cfg.get("backend", "mock")
    label_map = cfg.get("label_map") or {}
    if backend == "mock":
        return MockDetector()
    if backend == "yolo":
        return YoloDetector(cfg["model_path"], conf=cfg.get("conf", 0.4),
                            imgsz=cfg.get("imgsz", 640), device=cfg.get("device"),
                            label_map=label_map)
    if backend == "rfdetr":
        return RFDetrDetector(cfg["model_path"], cfg["class_names"], conf=cfg.get("conf", 0.4),
                              size=cfg.get("rfdetr_size", "base"), label_map=label_map)
    raise ValueError(f"알 수 없는 탐지기 backend: {backend} (mock / yolo / rfdetr)")
