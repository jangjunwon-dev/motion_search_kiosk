# data/ — 데이터셋

> 실제 이미지는 용량이 커서 **GitHub에 올리지 않습니다.** 공유 드라이브를 사용하고, 여기에는 구조와 규칙만 둡니다.
> 공유 드라이브: [Google Drive `motion_search_kiosk/data`](https://drive.google.com/drive/folders/18Jj_oCxZaz6I4CqoPXzT_9pQLqW0yDSM)

## 폴더 규칙

```
data/
├── sample/        # 테스트·시연용 소량 (커밋 O, 장당 200KB 이하, 10장 이내)
├── raw/           # 원본 (공유 드라이브) — HaGRID 등 받은 그대로, 절대 수정 금지
└── processed/     # 변환본 (공유 드라이브) — training/prepare_hagrid.py 결과
    └── hagrid_v1/ #   yolo/(data.yaml 포함) + coco/
```

## 사용 데이터: HaGRID (HAnd Gesture Recognition Image Dataset)

- 출처: https://github.com/hukenovs/hagrid (v2) · v1 은 같은 저장소 `hagrid_v1` 브랜치
- 라이선스: CC BY-SA 4.0 → 발표·보고서에 출처 표기
- 손 박스 + 제스처 라벨이 이미 있음 → **라벨링 없이** 바로 객체탐지 학습 가능
- 전체는 수백 GB → **필요한 6개 클래스만**, 그것도 **경량판(512px) 또는 subsample** 로 받기
  - 공식 `download.py` 의 `--targets one fist palm like dislike peace` 옵션으로 클래스만 선택
  - 또는 Kaggle 의 HaGRID 축소판(예: 384p/512p sample) — 받은 출처를 아래 표에 기록
- 주석 형식: `annotations/<split>/<class>.json` → `{"이미지ID": {"bboxes": [[x,y,w,h], ...], "labels": [...]}}`
  (x, y = 왼쪽 위, 모두 0~1 정규화)

## 변환

```powershell
python training/prepare_hagrid.py --ann-dir data/raw/hagrid/annotations `
    --images-root data/raw/hagrid/images --out data/processed/hagrid_v1 `
    --classes one fist palm like dislike peace --max-per-class 3000 --format both
```

## 📋 데이터 버전 기록

| 버전 | 원본 출처 | 클래스 | 장수 (train/val/test) | 변환 옵션 | 날짜 | 담당 |
|---|---|---|---|---|---|---|
| `hagrid_v1` | | one, fist, palm, like, dislike, peace | | `--max-per-class 3000` | | 🅐 |

## 우리 데이터 추가 (선택, 성능 개선용)
키오스크 설치 환경(복도·조명·거리 1~2m)과 HaGRID 가 다르면 오탐이 생길 수 있습니다.
→ 시연 장소에서 직접 찍은 사진을 소량(클래스당 50장) 라벨링(Roboflow / CVAT, YOLO 형식)해 `data/processed/custom_v1/` 로 추가 학습 — 결과는 `docs/experiments.md` 에 비교 기록.
