"""키오스크 콘텐츠 규칙 검사 — 실제 정보는 출처(source)가 있어야 하고, 확인 안 된 정보는 '(예시)' 표기."""

import json

from kiosk.config import ROOT


def load():
    p = ROOT / "web" / "content" / "kiosk_content.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_필수_항목():
    c = load()
    assert c["title"] and c["categories"]
    for cat in c["categories"]:
        assert {"id", "icon", "name", "desc", "items"} <= cat.keys()
        assert cat["items"], f"{cat['id']} 항목이 비어 있음"
        for it in cat["items"]:
            assert {"title", "subtitle", "body"} <= it.keys()


def test_출처_없는_정보는_예시_표기():
    for cat in load()["categories"]:
        if cat["id"] == "help":  # 사용법 안내는 사실 정보가 아님
            continue
        for it in cat["items"]:
            text = " ".join(str(it.get(k, "")) for k in ("title", "subtitle", "body"))
            assert it.get("source") or "(예시)" in text, \
                f"[{cat['name']}] '{it['title']}': 출처(source)를 적거나 '(예시)' 표기 필요"


def test_메뉴_가격_형식():
    """메뉴는 원 단위 정수 가격, 세트 가격은 단품보다 비싸야 함 (장바구니 합계 계산용)."""
    for cat in load()["categories"]:
        if cat["id"] == "help":
            continue
        for it in cat["items"]:
            assert it.get("id"), f"'{it['title']}' 에 id 필요 (장바구니 키)"
            assert isinstance(it.get("price"), int) and it["price"] > 0, it["title"]
            if "set_price" in it:
                assert it["set_price"] > it["price"], it["title"]
