# 01. Git 협업 규칙

> 2명이 3주 안에 끝내야 하므로 **규칙은 최소한, 대신 꼭 지킨다.**

## 1. 브랜치 전략 (GitHub Flow)

```
main  ─────●────────●────────●───────▶   (항상 실행되는 상태 유지)
            \      /  \      /
feat/model-yolo26 ●─●   feat/app-swipe ●─●
```

- `main` 에 **직접 push 금지** → 반드시 PR
- 브랜치 이름: `종류/파트-내용`

| 종류 | 예시 |
|---|---|
| `feat/` 새 기능 | `feat/model-yolo26-train`, `feat/app-dwell-click`, `feat/web-help-screen` |
| `fix/` 버그 | `fix/app-cursor-jitter` |
| `docs/` 문서 | `docs/update-roadmap` |
| `chore/` 설정 | `chore/ci-cache` |

## 2. 하루 작업 루틴

```powershell
# 시작할 때
git switch main
git pull
git switch -c feat/app-dwell-click         # 이미 있으면 git switch 브랜치명 후 git rebase main

# 작업 중 (자주, 작게)
python -m pytest
git add -p
git commit -m "feat(app): dwell 클릭 진행 링 추가"

# 끝낼 때
git push -u origin feat/app-dwell-click
# GitHub 웹에서 Pull Request 생성 (또는 gh pr create --fill)
```

## 3. 커밋 메시지

```
<종류>(<범위>): <한 줄 요약>
```
- 종류: `feat` `fix` `docs` `refactor` `test` `chore`
- 범위: `model` `app` `web` `docs` `scripts`
- 예: `fix(app): 손이 사라진 뒤 커서가 남아있는 문제 수정`

## 4. PR 규칙

1. PR 템플릿 체크리스트 채우기 — 특히 **"작동 원리를 내 말로 설명할 수 있음"**
2. **상대방 1명 승인** 후 머지 (CI 테스트 ✅ 필수)
3. 머지 방식: **Squash and merge**, 머지 후 브랜치 삭제
4. 탐지 결과 형식·클래스 이름·이벤트 이름 변경 PR은 Issue 로 먼저 합의

## 5. 절대 커밋하지 않는 것 (`.gitignore` 처리됨)

- `.venv/`, `runs/`, `logs/`
- 데이터 `data/*`, 가중치 `models/*.pt|pth` → **공유 드라이브**, 경로·기록만 README 에
- API 키, `kaggle.json`, `.env`

## 6. 충돌(conflict)이 났을 때

```powershell
git switch feat/내브랜치
git fetch origin
git rebase origin/main          # 충돌 파일 열어서 <<<< ==== >>>> 정리
git add <수정한파일>
git rebase --continue
git push --force-with-lease     # 내 브랜치에만! main 에는 절대 금지
```

## 7. GitHub 저장소 설정 (관리자 장준원 1회)

- [ ] Settings → Collaborators → **`himmelmin`** 초대 (Write 권한) → 팀원이 메일/알림에서 수락
- [ ] Settings → Branches → `main` 보호 규칙: *Require a pull request* (승인 1), *Require status checks* (CI `test`)
- [ ] Settings → General → *Allow squash merging* 만 체크, *Automatically delete head branches* 체크
- [ ] About 에 설명·토픽(`object-detection`, `yolo`, `hand-gesture`, `kiosk`) 추가
