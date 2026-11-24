# Copilot 지침

이 저장소의 공통 AI 지침은 루트의 `AGENTS.md` 입니다. 반드시 그 규칙을 따르세요.

핵심 요약:
- 서비스: FastAPI + WebSocket + 순수 HTML/CSS/JS (프론트 프레임워크 추가 금지)
- 탐지기: YOLO26(주력) / RF-DETR(비교). torch·ultralytics·rfdetr 는 `kiosk/detector.py` 안에서만 지연 import
- 탐지 결과 형식(`Detection`)·클래스 이름·WebSocket 이벤트 이름은 2명 합의 없이 수정 금지
- 임계값은 `configs/app.yaml`, 콘텐츠는 `web/content/kiosk_content.json`
- 주석·UI 문구는 한국어, 식별자는 영어. PEP 8(줄 길이 99). `python -m pytest` 통과 필수
