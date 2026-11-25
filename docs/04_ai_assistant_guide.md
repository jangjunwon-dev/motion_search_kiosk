# 04. 내 AI에 프로젝트 인식시키기

> 각자 Claude, Codex, ChatGPT, Gemini 등 쓰는 AI가 달라도 **같은 규칙·같은 진행 상황**을 알고 답하게 하는 방법입니다.
> 핵심 파일은 루트의 **`AGENTS.md`** 하나. 나머지는 모두 이것을 불러옵니다.

## 📄 저장소의 AI용 파일

| 파일 | 자동으로 읽는 도구 | 내용 |
|---|---|---|
| `AGENTS.md` | Codex, Cursor, Copilot 등 | **원본** — 요약·환경·구조·규칙 |
| `CLAUDE.md` | Claude Code | `@AGENTS.md` + Claude 전용 메모 |
| `GEMINI.md` | Gemini CLI | `@AGENTS.md` |
| `.github/copilot-instructions.md` | GitHub Copilot | 핵심 요약 |
| `docs/02_roadmap.md` · `docs/03_architecture.md` | (AI가 작업 전 읽도록 지시됨) | 현재 단계 · 약속 |

> ✏️ 규칙을 바꾸려면 **`AGENTS.md`만 수정**하세요.

## A. 터미널/IDE 코딩 AI — 가장 확실

저장소 폴더에서 실행하면 **자동으로** 지침을 읽습니다.

```powershell
cd motion_search_kiosk
claude        # Claude Code → CLAUDE.md → AGENTS.md
codex         # Codex → AGENTS.md
gemini        # Gemini CLI → GEMINI.md → AGENTS.md
```
Cursor·VS Code Copilot 은 폴더를 열면 됩니다.

내 파트 기억시키기 (개인 설정, 저장소에 안 올라감) — 예: `~/.claude/CLAUDE.md` 또는 `~/.codex/AGENTS.md`
```markdown
# 개인 설정
- motion_search_kiosk 프로젝트에서 나는 장준원, 🅑 키오스크 서비스(kiosk/, web/) 담당이다.
```

## B. 웹 채팅 AI (claude.ai, ChatGPT 등)

웹 채팅은 저장소를 자동으로 읽지 못하므로 **프로젝트(Project) 기능**에 자료를 넣어둡니다.

1. 새 프로젝트 "모션인식 탐색 키오스크" 만들기
2. 지식(Knowledge) 파일로 업로드: `AGENTS.md`, `docs/02_roadmap.md`, `docs/03_architecture.md`, 내 파트의 핵심 코드(`kiosk/gestures.py` 등)
3. 프로젝트 지침(Instructions)에 붙여넣기:
   ```
   이 프로젝트는 업로드한 AGENTS.md 규칙을 따른다. 나는 (장준원/성민수), (🅑/🅐) 담당이다.
   답변 전 02_roadmap.md 로 현재 단계를 확인하고, Windows PowerShell 명령으로 답한다.
   코드를 주면 발표 때 내가 설명할 수 있도록 작동 원리를 3줄로 같이 설명한다.
   ```
4. 로드맵이 바뀌면 파일을 다시 올리기

## C. 생성형 AI 사용 원칙 (과제 규정 — 중요)

> "코드 작성에 생성형 AI를 사용 가능. 단, **구현 내용과 작동 원리를 직접 설명할 수 있어야** 함"

- AI가 준 코드는 **한 줄씩 읽고**, `docs/06_how_it_works.md` 에 자기 말로 요약할 수 있을 때만 커밋
- AI에게 "이 코드가 왜 이렇게 동작하는지 학부생 수준으로 설명해줘", "교수님이 물어볼 만한 질문 5개" 를 꼭 같이 요청
- 성능 수치는 AI에게 묻지 말고 **직접 측정** (`training/evaluate.py`, `eval_commands.py`)
