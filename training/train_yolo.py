"""YOLO 손동작 탐지 모델 학습 (Ultralytics).

GPU가 없으면 Colab 사용 권장 → training/colab_train.ipynb

사용 예
    python training/train_yolo.py --data data/processed/hagrid_v1/yolo/data.yaml \
        --model yolo26n.pt --epochs 50 --imgsz 640 --name gesture_yolo26n

학습이 끝나면 runs/detect/<name>/weights/best.pt 를 models/<name>.pt 로 복사합니다.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="yolo26n.pt",
                    help="사전학습 가중치: yolo26n.pt / yolo26s.pt / yolo11n.pt 등")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=None, help="0 / cpu")
    ap.add_argument("--name", default="gesture_yolo26n")
    ap.add_argument("--project", default="runs/detect")
    args = ap.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        device=args.device, project=args.project, name=args.name, exist_ok=True,
        patience=15,
        # 좌우 반전 증강 유지: 손 모양 클래스는 좌우 대칭 → 왼손·오른손 모두 학습되는 효과
        fliplr=0.5,
        # 조명이 다양한 실내 환경 대비 색 증강을 약간 강하게
        hsv_v=0.5,
    )
    best = Path(args.project) / args.name / "weights" / "best.pt"
    if best.exists():
        Path("models").mkdir(exist_ok=True)
        dst = Path("models") / f"{args.name}.pt"
        shutil.copy2(best, dst)
        print(f"✅ 가중치 복사 완료 → {dst}")
        print("   공유 드라이브 models/ 에도 올리고 models/README.md 표를 갱신하세요.")


if __name__ == "__main__":
    main()
