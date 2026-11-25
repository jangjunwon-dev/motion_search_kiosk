# AGENTS.md — AI 코딩 도구 공통 지침

> Codex, Claude Code, Cursor, Gemini CLI, Copilot 등 **모든 AI 도구가 먼저 읽는 프로젝트 컨텍스트**입니다.
> 팀원 2명이 각자 다른 AI를 써도 같은 규칙으로 작업하도록 하는 것이 목적입니다. 내용을 바꾸면 PR로 공유하세요.

## 1. 프로젝트 한 줄 요약
**모션인식 탐색 키오스크** — 웹캠 영상에서 손동작(one, fist, palm, like, dislike, peace)을 **객체탐지(YOLO26 주력, RF-DETR 비교)** 로 찾고,
시간 축 해석(다수결·궤적·유지 시간)으로 커서·클릭·스와이프·확인·뒤로·홈 명령을 만들어 **웹 키오스크 화면을 비접촉으로 조작**하는 2인 학부 팀 프로젝트
(전주대학교 인공지능학과, 객체탐지(첨단) 기말프로젝트, 발표 12/14 또는 12/16).

## 1-1. 팀 구성
| 파트 | 담당 | 폴더 |
|---|---|---|
| 🅐 손동작 탐지 모델 (데이터·학습·성능평가) | 성민수 (GitHub `himmelmin`) | `training/`, `models/`, `data/` |
| 🅑 키오스크 서비스 (제스처 해석·웹·통합) + 저장소 관리 | 장준원 | `kiosk/`, `web/`, `configs/` |

## 2. 고정된 환경 (임의로 바꾸지 말 것)
- Python 3.11~3.13 (권장 3.12), 가상환경 `.venv`
- 서비스: FastAPI + uvicorn[standard](WebSocket 필수) + OpenCV + 순수 HTML/CSS/JS (**프론트 프레임워크·번들러 추가 금지** — 시연 PC에서 바로 실행돼야 함)
- 탐지: Ultralytics(YOLO26), rfdetr — **무거운 라이브러리는 `kiosk/detector.py` 안에서 지연 import** (mock 모드·테스트가 torch 없이 돌아야 함)
- 학습: Colab GPU 기준 (`training/colab_train.ipynb`)
- MediaPipe 등 랜드마크 모델로 **탐지기를 대체하지 말 것** (과제 조건이 객체탐지 모델 활용). 비교용 참고 정도는 사용자와 상의 후.

## 3. 저장소 구조
```
configs/app.yaml        카메라·탐지기·제스처 임계값 (하드코딩 대신 여기)
kiosk/gestures.py       🅑 탐지 결과 → 명령 (ROS/카메라 의존 없는 순수 로직, pytest 필수)
kiosk/detector.py       🅐🅑 공동 — 탐지기 래퍼 (Detection 형식은 합의 사항)
kiosk/engine.py         🅑 카메라 루프·미리보기·이벤트 CSV 로그
kiosk/server.py         🅑 FastAPI + WebSocket
web/                    🅑 키오스크 화면, web/content/kiosk_content.json (예시 콘텐츠)
training/               🅐 HaGRID 변환·YOLO/RF-DETR 학습·평가
tests/                  pytest
data/  models/          공유 드라이브 — 규칙은 각 README.md
docs/                   환경·Git·로드맵·아키텍처·AI 가이드·발표·작동원리
```

## 4. 실행 / 테스트 명령
```bash
python -m pip install -r requirements.txt      # 서비스 + 테스트
python -m pip install -r requirements-model.txt  # 모델 추론/학습 (torch 포함)
python -m pytest                               # 반드시 통과
python -m kiosk --mock                         # 카메라·모델 없이 화면 확인
python -m kiosk                                # 웹캠 + YOLO
python -m kiosk --video 영상.mp4                # 웹캠 대신 녹화 영상 (재현 테스트·시연 백업)
```
코드를 수정했다면 **`python -m pytest` 통과** 를 확인한 뒤 완료라고 보고할 것.

## 5. 인터페이스 약속 (상세: `docs/03_architecture.md`)
- 탐지 결과: `Detection(label: str, conf: float, box: (x1, y1, x2, y2) 0~1 정규화)`
- 클래스 이름: `one, fist, palm, like, dislike, peace` (+ 선택 `no_gesture`). 다른 이름의 모델은 `configs/app.yaml` 의 `label_map` 으로 맞춤
- WebSocket 이벤트 `type`: `cursor, click, swipe(direction), hold(progress), confirm, back, home, hand_lost, status`
- 위 세 가지를 바꿔야 하면 **코드를 바꾸지 말고** 변경 제안을 정리해 사용자에게 알릴 것 (2명 합의 사항)

## 6. 코딩 규칙
- Python: PEP 8, 최대 줄 길이 99, 타입 힌트 권장
- 주석·로그·문서·UI 문구는 **한국어**, 식별자는 영어 snake_case (JS 는 camelCase)
- 임계값·경로는 `configs/app.yaml` 로. 새 의존성은 `requirements*.txt` 에 반드시 추가
- 콘텐츠(건물·식단 등)는 `web/content/kiosk_content.json` 에만. **사실 확인 안 된 정보는 "(예시)" 표기 유지**
- 성능 수치(mAP, FPS, 인식률)는 실제로 측정한 값만 `docs/experiments.md` 에 기록 — 추정치·지어낸 값 금지

## 7. Git 규칙 (상세: `docs/01_git_workflow.md`)
- `main` 직접 push 금지, 브랜치 `feat/<파트>-<내용>` (파트: model / app / docs) → PR → 상대 1명 리뷰 → Squash merge
- 커밋: `feat(app): 요약` 형식 (종류: feat/fix/docs/refactor/test/chore, 범위: model/app/web/docs/scripts)
- `.venv/ data/** models/*.pt models/*.pth runs/ logs/` 커밋 금지
- AI는 사용자가 명시적으로 요청하지 않으면 commit/push 하지 말 것

## 8. AI가 작업 전에 확인할 것
1. `docs/02_roadmap.md` — 현재 단계와 내 파트의 다음 할 일
2. 사용자가 누구인지(팀원=🅐, 장준원=🅑) — 모르면 먼저 물어볼 것
3. 상대 파트 폴더를 수정해야 하면 수정 전에 사용자에게 알릴 것
4. 새 코드를 쓰면 `docs/06_how_it_works.md` 에 **발표 때 설명할 수 있는 수준의 원리 설명**을 추가/갱신 제안 (과제 규정: AI로 짠 코드도 직접 설명 가능해야 함)
5. 작업을 마치면 로드맵 체크박스 갱신 제안

## 9. 답변 스타일
- 사용자는 객체탐지 수업을 듣는 학부생 → 명령어는 복사해서 바로 실행 가능하게, 왜 필요한지 한 줄 설명
- Windows PowerShell 기준 명령을 먼저 제시
- 한국어 존댓말로 답변
