# 00. 환경 구축

> 목표: 두 사람 모두 `python scripts/check_env.py` 가 **전부 ✅**, `python -m kiosk --mock` 화면이 뜨는 상태.
> 실행 PC 는 Windows 기준으로 적었습니다. (macOS/Linux 명령은 각 단계 아래)

## 1. 준비물

| 항목 | 내용 |
|---|---|
| Python | **3.12 권장** (3.11~3.13). 3.14 이상은 torch·ultralytics 휠이 없을 수 있어 비권장 |
| Git | https://git-scm.com — 설치 후 `git config --global user.name "이름"` / `user.email` |
| 편집기 | VS Code + Python 확장 |
| 웹캠 | 노트북 내장 카메라로 충분 (시연 때는 720p 이상 외장 USB 권장) |
| 브라우저 | Chrome 또는 Edge (전체 화면 `F11`) |
| GPU | 없어도 됨 — 학습은 Colab, 추론은 CPU 로 YOLO26n 사용 |

> Python 여러 버전이 있으면 Windows 에서는 `py -3.12` 로 원하는 버전을 고릅니다. (`py -0` 으로 설치된 버전 확인)
> 이미 `pip`/`python` 이 PATH 에 없다는 오류가 나면 `py -3.12 -m pip ...` 처럼 `py` 런처를 쓰세요.

## 2. 저장소 받기 + 가상환경

```powershell
cd ~\Documents
git clone https://github.com/jangjunwon-dev/motion_search_kiosk.git
cd motion_search_kiosk
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # 프롬프트 앞에 (.venv) 가 보이면 성공
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> `Activate.ps1` 실행이 막히면(보안 오류) 한 번만: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

macOS / Linux:
```bash
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 3. 점검

```powershell
python scripts/check_env.py --camera
python -m pytest
python -m kiosk --mock           # 브라우저가 열리면 성공. 마우스를 손 커서처럼 움직여 보기
```

## 4. 실제 모드 (모델 추론) — 🅐 는 필수, 🅑 는 통합 단계에서

```powershell
# NVIDIA GPU 가 있으면 먼저 https://pytorch.org 에서 CUDA 버전 torch 설치 명령 실행
python -m pip install -r requirements-model.txt
# 공유 드라이브 models/ 에서 gesture_yolo26n.pt 받아 저장소 models/ 에 넣기
python -m kiosk
```

## 5. 학습 환경 (🅐) — Google Colab

1. Colab 에서 `training/colab_train.ipynb` 열기 (GitHub 탭 → 저장소 주소)
2. 런타임 → 런타임 유형 변경 → **T4 GPU**
3. 노트북 셀을 위에서부터 실행 — 공유 드라이브를 마운트해 데이터·결과를 드라이브에 저장합니다
4. 학습이 끝나면 `best.pt` 가 공유 드라이브 `models/` 에 복사됨 → `models/README.md` 표 갱신

## 6. VS Code 권장 설정

- 인터프리터 선택: `Ctrl+Shift+P` → *Python: Select Interpreter* → `.venv`
- 터미널 기본 프로필: PowerShell
- 테스트 탐색기: *Python: Configure Tests* → pytest → `tests`

## 7. 자주 나는 문제

| 증상 | 해결 |
|---|---|
| 화면은 뜨는데 오른쪽 위가 "서버 연결 끊김" | `uvicorn[standard]` 미설치 → `python -m pip install "uvicorn[standard]"` (WebSocket 필요) |
| "카메라를 열 수 없습니다" | Zoom·Teams 등 카메라 쓰는 앱 종료, `configs/app.yaml` 의 `camera.index` 를 1 로 |
| 커서가 반대로 움직임 | `gesture.mirror` 를 true/false 바꿔보기 |
| 커서가 덜덜 떨림 | `gesture.cursor_alpha` 를 0.2 로 낮추기 |
| 화면 끝까지 커서가 안 감 | `gesture.active_region` 범위를 좁히기 (예: `[0.25, 0.15, 0.75, 0.70]`) |
| FPS 가 너무 낮음 (CPU) | `detector.imgsz: 416`, YOLO26**n** 사용, `camera.width/height: 640/480` |
| `ModuleNotFoundError: ultralytics` | 실제 모드는 `requirements-model.txt` 설치 필요 (mock 은 불필요) |
