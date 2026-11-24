# ✋ 모션인식 탐색 키오스크 (Motion Search Kiosk)

> **화면을 만지지 않고 손동작만으로 정보를 찾아보는 비접촉 안내 키오스크**
> 카메라 영상에서 **손동작을 객체탐지(YOLO26 / RF-DETR)** 로 찾고, 그 결과를 커서 이동·선택·페이지 넘김·확인·뒤로 같은 **키오스크 명령**으로 바꿔 웹 화면을 조작합니다.
> 객체탐지(첨단) 기말프로젝트 — 전주대학교 인공지능학과

| 항목 | 내용 |
|---|---|
| 탐지 모델 | **Ultralytics YOLO26** (주력) · **RF-DETR** (비교) — 손동작 6종 탐지 |
| 데이터 | **HaGRID** 손동작 데이터셋 (클래스: one, fist, palm, like, dislike, peace) |
| 서비스 | Python **FastAPI** 백엔드 + **WebSocket** + HTML/CSS/JS 키오스크 화면 |
| 실행 환경 | Windows 11 / macOS / Linux, Python 3.11~3.13, 웹캠 1대 |
| 학습 | Google Colab (GPU) 또는 개인 GPU |
| 협업 | GitHub (feature 브랜치 → PR → `main`) |
| 공유 드라이브 | [Google Drive `motion_search_kiosk`](https://drive.google.com/drive/folders/1nrDPbWXCH7-d1SPKkaVqSvlkxN9dqZqS) — `data/` `models/` `발표·보고서/` `시연영상/` |
| 발표 | **12월 14일(월) 또는 16일(수)** — 15분 (PPT + 서비스 시연) |

---

## 👥 팀 구성 및 역할 (2인)

| 파트 | 담당 | 주요 폴더 | 브랜치 접두어 |
|---|---|---|---|
| 🅐 손동작 탐지 모델 (데이터·학습·성능평가) | **팀원 (GitHub `himmelmin`)** | `training/`, `models/`, `data/` | `feat/model-*` |
| 🅑 키오스크 서비스 (제스처 해석·웹 화면·통합) | **장준원** (저장소 관리) | `kiosk/`, `web/`, `configs/` | `feat/app-*` |

> 역할은 임시 배정입니다. 바꾸려면 이 표와 `AGENTS.md`, `.github/CODEOWNERS` 를 함께 수정하세요.
> 두 파트의 약속(탐지 결과 형식·클래스 이름·이벤트 이름)은 [docs/03_architecture.md](docs/03_architecture.md) — **둘이 합의 후에만** 수정합니다.

---

## 💡 왜 이 서비스인가 (주제 선정 배경 요약)

- **위생**: 병원·관공서·식당 키오스크 화면은 하루 수백 명이 만지는 접촉면
- **접근성**: 휠체어 사용자·키가 작은 사람은 높은 화면 위쪽 버튼에 손이 닿지 않음, 장갑·젖은 손·손이 불편한 사람도 터치가 어려움
- **단순 탐지가 아닌 서비스**: 박스를 그리는 데서 끝나지 않고, 탐지 결과를 시간 축으로 해석(안정화·궤적·유지 시간)해 **실제로 조작 가능한 UI** 를 만든다

자세한 발표 구성: [docs/05_presentation_guide.md](docs/05_presentation_guide.md)

---

## 🖐️ 손동작 → 명령

| 손동작 (HaGRID 클래스) | 명령 | 판정 방식 |
|---|---|---|
| ☝️ 검지 (`one`) | 커서 이동 | 손 박스 위쪽 중앙 → 화면 좌표, 좌우 반전 + 평활화 |
| ☝️ → ✊ (`one` → `fist`) | 선택(클릭) | 가리키다 0.8초 안에 주먹으로 바뀌면 |
| ☝️ 가만히 1.5초 | 선택(클릭) | 같은 버튼 위에 머무르면 (dwell) |
| ✋ 좌우로 쓸기 (`palm`) | 다음/이전 페이지 | 0.45초 안에 가로 18% 이상 이동, 세로 흔들림 12% 이하 |
| 👍 (`like`) 0.7초 유지 | 확인 | 유지 시간 게이지 |
| 👎 (`dislike`) 0.7초 유지 | 뒤로 | 〃 |
| ✌️ (`peace`) 0.7초 유지 | 처음 화면 | 〃 |

공통: 최근 5프레임 다수결로 깜빡임 제거 · 가장 큰 손 1개만 사용(뒤에 지나가는 사람 무시) · 명령 후 0.9초 쿨다운

---

## 🚀 처음 시작하는 팀원 (순서대로)

1. **환경 구축** → [docs/00_environment_setup.md](docs/00_environment_setup.md)
2. **Git 협업 규칙** → [docs/01_git_workflow.md](docs/01_git_workflow.md)
3. **진행 계획·현황** → [docs/02_roadmap.md](docs/02_roadmap.md)
4. **시스템 구조·약속** → [docs/03_architecture.md](docs/03_architecture.md)
5. **내 AI에 프로젝트 인식시키기** → [docs/04_ai_assistant_guide.md](docs/04_ai_assistant_guide.md)
6. **발표 준비** → [docs/05_presentation_guide.md](docs/05_presentation_guide.md)
7. **코드 작동 원리 (발표 때 직접 설명해야 함!)** → [docs/06_how_it_works.md](docs/06_how_it_works.md)

```powershell
# Windows PowerShell (macOS/Linux 는 docs/00 참고)
git clone https://github.com/jangjunwon-dev/motion_search_kiosk.git
cd motion_search_kiosk
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/check_env.py           # 환경 점검 — 전부 ✅ 여야 함
```

## ▶️ 실행

```powershell
# 1) mock 모드 — 카메라·모델 없이 화면만 (마우스 = 손 커서, ←/→ = 스와이프, Enter = 확인, Backspace = 뒤로, H = 처음, P = 카메라 미리보기)
python -m kiosk --mock

# 2) 실제 모드 — 웹캠 + 학습한 YOLO 모델 (models/gesture_yolo26n.pt 필요)
python -m kiosk

# 3) RF-DETR 로 바꿔 실행 (성능 비교 시연용)
python -m kiosk --backend rfdetr --model models/gesture_rfdetr_base.pth
```

브라우저가 자동으로 `http://127.0.0.1:8000` 을 엽니다. 전체 화면은 `F11`.

## 🧪 테스트

```powershell
python -m pytest            # 제스처 규칙·데이터 변환·서버 흐름 테스트 (모델·카메라 불필요)
```

---

## 📁 저장소 구조

```
motion_search_kiosk/
├── AGENTS.md                 # AI 코딩 도구 공통 컨텍스트 (Codex, Cursor 등)
├── CLAUDE.md / GEMINI.md     # 각 AI 용 (AGENTS.md 를 불러옴)
├── configs/app.yaml          # 카메라·모델·제스처 임계값 설정
├── kiosk/                    # 🅑 서비스 백엔드
│   ├── gestures.py           #   탐지 결과 → 명령 (순수 로직, 테스트 대상)
│   ├── detector.py           #   YOLO / RF-DETR / mock 탐지기 래퍼
│   ├── engine.py             #   카메라 → 탐지 → 해석 루프, 미리보기, 이벤트 로그
│   ├── server.py             #   FastAPI + WebSocket
│   └── __main__.py           #   python -m kiosk
├── web/                      # 🅑 키오스크 화면 (HTML/CSS/JS, content/*.json)
├── training/                 # 🅐 데이터 변환·학습·평가
│   ├── prepare_hagrid.py     #   HaGRID → YOLO / COCO 변환
│   ├── train_yolo.py         #   YOLO26 학습
│   ├── train_rfdetr.py       #   RF-DETR 학습 (비교)
│   ├── colab_train.ipynb     #   Colab 에서 한 번에 학습
│   ├── evaluate.py           #   mAP · 지연시간/FPS
│   ├── eval_commands.py      #   명령 인식률 (시나리오 vs 실제 로그)
│   └── scenarios/            #   성능평가 시나리오
├── tests/                    # pytest
├── scripts/check_env.py      # 환경 점검
├── data/                     # 데이터 — 구조·설명서만 커밋 (data/README.md)
├── models/                   # 가중치 — 공유 드라이브 (models/README.md)
└── docs/                     # 가이드·계획·설계·발표·작동원리
```

---

## 🤖 생성형 AI 사용 원칙 (과제 규정)

코드 작성에 생성형 AI를 쓸 수 있지만, **구현 내용과 작동 원리를 직접 설명할 수 있어야 합니다.**
→ 코드를 받아들이기 전에 [docs/06_how_it_works.md](docs/06_how_it_works.md) 의 해당 부분을 **자기 말로 설명할 수 있는지** 확인하고, 설명이 안 되는 코드는 머지하지 않습니다.
