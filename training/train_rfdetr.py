"""RF-DETR 손동작 탐지 모델 학습 (YOLO 와 성능 비교용).

prepare_hagrid.py --format coco 로 만든 폴더를 사용합니다.
    data/processed/hagrid_v1/coco/{train,valid,test}/_annotations.coco.json

사용 예
    python training/train_rfdetr.py --dataset data/processed/hagrid_v1/coco --size base \
        --epochs 20 --batch 4 --output runs/rfdetr/gesture_rfdetr_base

학습 결과의 checkpoint_best_total.pth 를 models/gesture_rfdetr_base.pth 로 복사합니다.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--size", default="base", choices=["nano", "small", "base", "medium"])
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4,
                    help="batch × grad_accum = 실효 배치 16 권장")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--output", default="runs/rfdetr/gesture_rfdetr_base")
    args = ap.parse_args()

    import rfdetr

    cls = {"nano": "RFDETRNano", "small": "RFDETRSmall", "base": "RFDETRBase",
           "medium": "RFDETRMedium"}[args.size]
    model = getattr(rfdetr, cls)()
    model.train(dataset_dir=args.dataset, epochs=args.epochs, batch_size=args.batch,
                grad_accum_steps=args.grad_accum, lr=args.lr, output_dir=args.output)

    for name in ("checkpoint_best_total.pth", "checkpoint_best_ema.pth", "checkpoint.pth"):
        ck = Path(args.output) / name
        if ck.exists():
            Path("models").mkdir(exist_ok=True)
            dst = Path("models") / f"gesture_rfdetr_{args.size}.pth"
            shutil.copy2(ck, dst)
            print(f"✅ 가중치 복사 완료 → {dst}")
            break


if __name__ == "__main__":
    main()
