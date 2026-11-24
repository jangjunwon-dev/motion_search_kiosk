# models/ — 학습된 모델 가중치

> 가중치 파일(`*.pt`, `*.pth`, `*.onnx`)은 **GitHub에 올리지 않습니다.** 공유 드라이브에서 받아 이 폴더에 둡니다.
> 공유 드라이브: [Google Drive `motion_search_kiosk/models`](https://drive.google.com/drive/folders/1q2Haz1n99AqQtkrMhgt8ve6sQu1UChOb)

## 기본 경로
- `configs/app.yaml` → `detector.model_path: models/gesture_yolo26n.pt`
- 다른 파일로 실행: `python -m kiosk --model models/파일명.pt`
- RF-DETR: `python -m kiosk --backend rfdetr --model models/gesture_rfdetr_base.pth`

## 📋 모델 기록 (측정한 값만 기입)

| 파일명 | 기반 모델 | 데이터 버전 | epochs / imgsz | mAP50 | mAP50-95 | CPU 지연(ms) | GPU 지연(ms) | 날짜 | 담당 |
|---|---|---|---|---|---|---|---|---|---|
| `gesture_yolo26n.pt` | yolo26n.pt | `hagrid_v1` | | | | | | | 🅐 |
| `gesture_yolo26s.pt` | yolo26s.pt | `hagrid_v1` | | | | | | | 🅐 |
| `gesture_rfdetr_base.pth` | RF-DETR Base | `hagrid_v1` (COCO) | | | | | | | 🅐 |

측정 방법: `training/evaluate.py` (mAP: test split, 지연: `kiosk/detector.py` 래퍼로 동일 이미지 200장)
