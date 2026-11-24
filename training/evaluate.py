"""탐지 모델 성능평가 — 정확도(mAP)와 속도(지연시간·FPS)를 같은 기준으로 측정.

1) 정확도
    python training/evaluate.py map --backend yolo --model models/gesture_yolo26n.pt \
        --data data/processed/hagrid_v1/yolo/data.yaml
    python training/evaluate.py map --backend rfdetr --model models/gesture_rfdetr_base.pth \
        --coco data/processed/hagrid_v1/coco/test

2) 속도 (키오스크에서 실제로 쓰는 kiosk.detector 래퍼로 측정 → 두 모델 공정 비교)
    python training/evaluate.py speed --backend yolo --model models/gesture_yolo26n.pt \
        --images data/processed/hagrid_v1/yolo/images/test --n 200

결과는 runs/eval/*.json 에 저장 → docs/experiments.md 표에 옮겨 적기
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kiosk.config import load_config  # noqa: E402
from kiosk.detector import build_detector  # noqa: E402


def save(result: dict, tag: str) -> Path:
    out = ROOT / "runs" / "eval"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{tag}_{datetime.now():%Y%m%d_%H%M%S}.json"
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 저장: {p}")
    return p


def eval_map_yolo(model: str, data: str, imgsz: int, split: str) -> dict:
    from ultralytics import YOLO

    m = YOLO(model).val(data=data, imgsz=imgsz, split=split, verbose=False)
    names = m.names
    per_class = {names[int(c)]: round(float(ap), 4)
                 for c, ap in zip(m.box.ap_class_index, m.box.ap50)}
    return {"backend": "yolo", "model": model, "split": split,
            "mAP50": round(float(m.box.map50), 4), "mAP50_95": round(float(m.box.map), 4),
            "precision": round(float(m.box.mp), 4), "recall": round(float(m.box.mr), 4),
            "AP50_per_class": per_class}


def eval_map_rfdetr(model: str, coco_dir: str, cfg: dict) -> dict:
    import supervision as sv
    from supervision.metrics import MeanAveragePrecision

    ds = sv.DetectionDataset.from_coco(images_directory_path=coco_dir,
                                       annotations_path=f"{coco_dir}/_annotations.coco.json")
    det_cfg = dict(cfg["detector"], backend="rfdetr", model_path=model, conf=0.001)
    det = build_detector(det_cfg)
    metric = MeanAveragePrecision()
    for _, image, target in ds:
        pred = det.model.predict(image[:, :, ::-1].copy(), threshold=0.001)
        metric.update(pred, target)
    r = metric.compute()
    return {"backend": "rfdetr", "model": model, "split": coco_dir,
            "mAP50": round(float(r.map50), 4), "mAP50_95": round(float(r.map50_95), 4)}


def eval_speed(backend: str, model: str, images: str, n: int, warmup: int, cfg: dict) -> dict:
    import cv2

    det_cfg = dict(cfg["detector"], backend=backend)
    if model:
        det_cfg["model_path"] = model
    det = build_detector(det_cfg)
    files = sorted([p for p in Path(images).iterdir() if p.suffix.lower() in (".jpg", ".png")])
    if not files:
        raise SystemExit(f"이미지가 없습니다: {images}")
    frames = [cv2.imread(str(files[i % len(files)])) for i in range(min(n, len(files)))]
    for f in frames[:warmup]:
        det.detect(f)
    times = []
    t_all = time.perf_counter()
    for i in range(n):
        _, ms = det.timed_detect(frames[i % len(frames)])
        times.append(ms)
    total = time.perf_counter() - t_all
    times.sort()
    return {"backend": backend, "model": model, "n": n,
            "latency_ms_mean": round(statistics.mean(times), 2),
            "latency_ms_p50": round(times[len(times) // 2], 2),
            "latency_ms_p95": round(times[int(len(times) * 0.95) - 1], 2),
            "fps": round(n / total, 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description="탐지 모델 성능평가")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("map")
    a.add_argument("--backend", choices=["yolo", "rfdetr"], required=True)
    a.add_argument("--model", required=True)
    a.add_argument("--data", help="YOLO data.yaml")
    a.add_argument("--coco", help="RF-DETR COCO 폴더 (예: .../coco/test)")
    a.add_argument("--imgsz", type=int, default=640)
    a.add_argument("--split", default="test")
    b = sub.add_parser("speed")
    b.add_argument("--backend", choices=["yolo", "rfdetr", "mock"], required=True)
    b.add_argument("--model", default=None)
    b.add_argument("--images", required=True)
    b.add_argument("--n", type=int, default=200)
    b.add_argument("--warmup", type=int, default=10)
    args = ap.parse_args()

    cfg = load_config()
    if args.cmd == "map":
        if args.backend == "yolo":
            res = eval_map_yolo(args.model, args.data, args.imgsz, args.split)
        else:
            res = eval_map_rfdetr(args.model, args.coco, cfg)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        save(res, f"map_{args.backend}")
    else:
        res = eval_speed(args.backend, args.model, args.images, args.n, args.warmup, cfg)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        save(res, f"speed_{args.backend}")


if __name__ == "__main__":
    main()
