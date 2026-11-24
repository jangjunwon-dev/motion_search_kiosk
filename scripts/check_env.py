"""환경 점검 — 팀원 둘 다 전부 ✅ 가 나와야 같은 환경입니다.

    python scripts/check_env.py            # 기본 점검
    python scripts/check_env.py --camera   # 웹캠도 열어보기
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok_all = True


def check(name: str, ok: bool, hint: str = "") -> None:
    global ok_all
    print(f"{'✅' if ok else '❌'} {name}" + ("" if ok or not hint else f"  → {hint}"))
    ok_all &= ok


def has(mod: str) -> tuple[bool, str]:
    try:
        m = importlib.import_module(mod)
        return True, getattr(m, "__version__", "")
    except Exception:
        return False, ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", action="store_true")
    args = ap.parse_args()

    v = sys.version_info
    check(f"Python {v.major}.{v.minor}", (3, 11) <= (v.major, v.minor) <= (3, 13),
          "Python 3.11~3.13 필요 (권장 3.12)")
    check("가상환경(.venv) 사용 중", sys.prefix != sys.base_prefix, ".venv 활성화 후 실행")
    for mod, pkg in [("fastapi", "fastapi"), ("uvicorn", "uvicorn[standard]"),
                     ("websockets", "uvicorn[standard]"), ("yaml", "pyyaml"),
                     ("cv2", "opencv-python"), ("numpy", "numpy"), ("pytest", "pytest")]:
        ok, ver = has(mod)
        check(f"{mod} {ver}", ok, f"pip install {pkg}")

    print("\n— 모델 (실제 모드에 필요, mock 모드는 없어도 됨) —")
    ok_t, ver_t = has("torch")
    print(f"{'✅' if ok_t else '⚪'} torch {ver_t}")
    if ok_t:
        import torch

        gpu = ("✅ " + torch.cuda.get_device_name(0) if torch.cuda.is_available()
               else "없음 (CPU 추론 — n 모델 권장)")
        print(f"   GPU: {gpu}")
    for mod in ("ultralytics", "rfdetr"):
        ok, ver = has(mod)
        print(f"{'✅' if ok else '⚪'} {mod} {ver}")
    models = sorted(p.name for p in (ROOT / "models").glob("*.p*t*"))
    listed = ", ".join(models) or "없음 (공유 드라이브에서 받기)"
    print(f"{'✅' if models else '⚪'} models/ 가중치: {listed}")

    if args.camera:
        import cv2

        cap = cv2.VideoCapture(0)
        ok, frame = cap.read() if cap.isOpened() else (False, None)
        check("웹캠 0번", ok, "다른 앱이 카메라를 쓰는지, configs/app.yaml camera.index 확인")
        if ok:
            print(f"   해상도 {frame.shape[1]}x{frame.shape[0]}")
        cap.release()

    print("\n" + ("🎉 기본 환경 OK — python -m kiosk --mock 실행해 보세요" if ok_all
                  else "⚠️ ❌ 항목을 해결한 뒤 다시 실행하세요"))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
