# 07. 🅐 모델 파트 — 첫 작업 안내 (성민수용)

> 🅐 손동작 탐지 모델 담당이 **처음 1주일 동안 할 일**을 순서대로 적었습니다. 위에서부터 그대로 따라 하면 됩니다.
> 목표: **12/03(수)까지 첫 모델 `gesture_yolo26n.pt` 를 공유 드라이브 `models/` 에 올리기**
> (🅑 장준원이 이 파일로 실제 웹캠 연결·튜닝을 시작합니다. 늦어질 것 같으면 미리 알려 주세요.)

| 단계 | 할 일 | 예상 시간 | 완료 기준 |
|---|---|---|---|
| 0 | GitHub 초대 수락 + 드라이브 바로가기 | 5분 | 저장소·드라이브 폴더가 보임 |
| 1 | 내 PC 환경 구축 | 30분 | `check_env.py` 전부 ✅, mock 화면 뜸 |
| 2 | 내 AI 에 프로젝트 인식시키기 | 10분 | AI 가 "🅐 모델 파트"라고 알아들음 |
| 3 | 데이터 받기 + 변환 (Colab) | 1시간 | 드라이브 `data/processed/hagrid_v1/` 생성 |
| 4 | YOLO26n 첫 학습 + 평가 (Colab) | 1~2시간 (대부분 기다림) | 드라이브 `models/gesture_yolo26n.pt` |
| 5 | 기록 + 첫 PR | 20분 | PR 생성, 🅑 리뷰 요청 |

---

## 0. 초대 수락 + 드라이브 바로가기 (5분)

1. **GitHub**: 이메일 또는 https://github.com/notifications 에서 `jangjunwon-dev/motion_search_kiosk` 초대 **Accept**
2. **Google Drive** (snns3434@jj.ac.kr 로그인): `공유 문서함` → `motion_search_kiosk` 폴더 우클릭 → **정리 → 바로가기 추가 → 내 드라이브**
   - 이걸 해야 Colab 에서 `/content/drive/MyDrive/motion_search_kiosk` 경로로 보입니다.

## 1. 내 PC 환경 구축 (30분)

자세한 설명은 [00_environment_setup.md](00_environment_setup.md). 핵심만:

```powershell
# Windows PowerShell — Python 3.12, Git 이 설치돼 있어야 함 (py -0 으로 확인)
cd ~\Documents
git clone https://github.com/jangjunwon-dev/motion_search_kiosk.git
cd motion_search_kiosk
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1                  # 막히면: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_env.py --camera          # 전부 ✅ 인지 확인
python -m pytest                              # 전부 passed
python -m kiosk --mock                        # 브라우저 화면이 뜨면 성공 (Ctrl+C 로 종료)
```

> 학습은 Colab 에서 하므로 PC 에 torch 를 깔 필요는 아직 없습니다.
> 내 PC 에서 모델을 직접 돌려보는 건 4단계 이후 `python -m pip install -r requirements-model.txt`.

`check_env.py` 결과 화면을 단톡방에 공유해 주세요.

## 2. 내 AI 에 프로젝트 인식시키기 (10분)

[04_ai_assistant_guide.md](04_ai_assistant_guide.md) 참고. 한 줄 요약:
- Claude Code / Codex 등 터미널 AI → 저장소 폴더에서 실행하면 `AGENTS.md` 를 자동으로 읽음
- 웹 채팅 AI → 프로젝트를 만들고 `AGENTS.md`, `docs/02_roadmap.md`, `docs/03_architecture.md` 업로드 + "나는 🅐 모델 파트 담당" 이라고 지침에 적기

## 3. 데이터 받기 + 변환 (Colab, 1시간)

### 어떤 데이터를 받나요?
HaGRID 원본은 클래스 하나가 약 40GB(6개면 250GB)라 받을 수 없습니다.
→ 원본을 384p 로 줄인 공개 축소판 **`cj-mills/hagrid-sample-120k-384p`** (Hugging Face, zip 약 3.5GB, 약 12.7만 장, 18클래스) 를 받아서
우리가 쓰는 **6클래스(one, fist, palm, like, dislike, peace)만** 뽑습니다.
- 라이선스 CC BY-SA 4.0 → 발표 자료에 출처 표기 (data/README.md 에 적어 둠)
- 더 크게 해보고 싶으면 나중에 `hagrid-sample-500k-384p` (13.4GB)

### Colab 에서 실행
1. https://colab.research.google.com → **GitHub** 탭 → `jangjunwon-dev/motion_search_kiosk` → `training/colab_train.ipynb` 열기
2. **런타임 → 런타임 유형 변경 → T4 GPU**
3. 노트북 **1)·2) 셀** 실행 (드라이브 연결, 저장소·패키지 설치)
4. 노트북의 3-a 대신 **새 코드 셀을 만들어** 아래를 실행 (원본은 Colab 디스크에 직접 받음 — 드라이브에 올릴 필요 없음):

```python
# (3-a 대체) HaGRID 축소판 다운로드 → 압축 해제 → 구조 확인
!wget -q --show-progress -O /content/hagrid.zip \
    https://huggingface.co/datasets/cj-mills/hagrid-sample-120k-384p/resolve/main/hagrid-sample-120k-384p.zip
!unzip -q /content/hagrid.zip -d /content/hagrid_raw && rm /content/hagrid.zip
!find /content/hagrid_raw -maxdepth 3 -type d | head -40      # 폴더 구조 확인
!find /content/hagrid_raw -name "one.json"                     # 주석 파일 위치 확인
```

5. 위 출력에서 **`one.json` 이 들어 있는 폴더** 를 `ANN` 으로, **이미지 폴더들의 상위 폴더** 를 `IMG` 로 적고 변환:

```python
ANN = '/content/hagrid_raw/여기에_주석폴더'      # 예: .../ann_train_val  (one.json 이 바로 들어 있는 폴더)
IMG = '/content/hagrid_raw/여기에_이미지상위폴더'
!python training/prepare_hagrid.py --ann-dir "$ANN" --images-root "$IMG" \
    --out /content/hagrid_v1 --classes one fist palm like dislike peace \
    --max-per-class 3000 --format both --copy
!mkdir -p "$DRIVE/data/processed" && cp -r /content/hagrid_v1 "$DRIVE/data/processed/"
```

- 변환 결과로 `[YOLO] train: ○○장`, `val`, `test` 장수가 출력됩니다 → **이 숫자를 메모** (5단계 기록용)
- 축소판은 주석이 train/val/test 로 나뉘어 있지 않아서, 스크립트가 **사람(user_id) 단위로 8:1:1** 로 자동으로 나눕니다.
  (같은 사람 사진이 학습과 테스트에 같이 들어가면 점수가 실제보다 높게 나오기 때문 — 발표 때 설명 포인트!)
- `⚠️ 주석을 찾지 못했습니다` 가 나오면 `ANN` 경로가 틀린 것

## 4. YOLO26n 첫 학습 + 평가 (Colab)

노트북의 **3-b → 4) → 5) → 6) 셀** 을 순서대로 실행합니다.

| 셀 | 하는 일 | 확인할 것 |
|---|---|---|
| 3-b | 드라이브 변환본 → Colab 디스크 복사 | `data.yaml` 내용이 출력됨 |
| 4) | YOLO26n 50 epoch 학습 | 끝나면 `models/gesture_yolo26n.pt` 생성. **걸린 시간 메모** |
| 5) | mAP + 속도 측정 | mAP50, mAP50-95, FPS 숫자 **메모** |
| 6) | 결과를 드라이브에 저장 | 드라이브 `models/gesture_yolo26n.pt`, `발표·보고서/실험결과/` |

> Colab 무료 GPU 는 오래 안 쓰면 끊깁니다. 학습 중 탭을 열어 두고, 끊기면 `--epochs 30` 으로 줄여 다시 실행하세요.
> 6) 셀까지 끝나면 **단톡방에 "모델 올림" 한 줄** → 🅑 가 바로 연결 테스트를 시작합니다.

## 5. 기록 + 첫 PR (20분)

**측정한 숫자만** 적습니다 (추정치 금지 — AGENTS.md 규칙).

```powershell
cd ~\Documents\motion_search_kiosk
git switch main; git pull
git switch -c feat/model-hagrid-v1
# 아래 3개 파일의 표를 채우기
#   data/README.md       → 데이터 버전 기록 (원본 출처: hagrid-sample-120k-384p, 장수 train/val/test)
#   models/README.md     → 모델 기록 (gesture_yolo26n.pt, mAP50 / FPS, 날짜)
#   docs/experiments.md  → 실험 한 줄 (설정·결과·걸린 시간)
#   docs/02_roadmap.md   → 🅐 체크박스 체크
git add data/README.md models/README.md docs/experiments.md docs/02_roadmap.md
git commit -m "docs(model): HaGRID v1 변환·YOLO26n 첫 학습 결과 기록"
git push -u origin feat/model-hagrid-v1
```

→ GitHub 웹에서 **Compare & pull request** → 리뷰어 `jangjunwon-dev` 지정 → 생성.
Git 규칙 자세히: [01_git_workflow.md](01_git_workflow.md)

---

## 그다음 (12/04~)
[02_roadmap.md](02_roadmap.md) 🅐 체크리스트 순서대로: YOLO26s 학습 → RF-DETR 학습 → 3종 비교표 → 발표 2)·5) 슬라이드.

## 발표 대비 — 지금부터 메모해 둘 것
- 왜 HaGRID 를 골랐나 (라벨이 이미 있음, 다양한 사람·배경·거리)
- 왜 사람 단위로 split 했나 (위 3단계 설명)
- YOLO26 이 어떤 모델인지 한 문단 (NMS 없는 구조, 경량 → CPU 실시간) — [06_how_it_works.md](06_how_it_works.md) 참고
- 학습 곡선·혼동행렬 그림 (`발표·보고서/실험결과/` 에 자동 저장됨)

## 막히면
- 오류 메시지 **전체를 복사** + 실행한 명령 + 화면 캡처를 단톡방에 → 같이 보기
- AI 에게 물을 때도 같은 3가지를 붙여서 질문
