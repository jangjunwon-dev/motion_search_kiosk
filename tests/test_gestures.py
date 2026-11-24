"""gestures.py 단위 테스트 — 카메라·모델 없이 제스처 → 명령 변환 규칙을 검증."""

from kiosk.gestures import Detection, GestureConfig, GestureInterpreter

FPS = 30
DT = 1 / FPS


def hand(label, cx=0.5, cy=0.5, size=0.2, conf=0.9):
    h = size / 2
    return Detection(label, conf, (cx - h, cy - h, cx + h, cy + h))


def feed(gi, frames, t0=0.0):
    """frames: [[Detection...], ...] → (모든 이벤트, 마지막 시각)"""
    events = []
    t = t0
    for dets in frames:
        events += gi.update(dets, t)
        t += DT
    return events, t


def types(events):
    return [e.type for e in events]


def test_작은손과_낮은신뢰도는_무시():
    gi = GestureInterpreter()
    assert gi.select_active_hand([hand("one", size=0.02)]) is None
    assert gi.select_active_hand([hand("one", conf=0.2)]) is None
    big = hand("one", size=0.3)
    assert gi.select_active_hand([hand("palm", size=0.15), big]) is big


def test_no_gesture_클래스는_무시():
    gi = GestureInterpreter()
    assert gi.select_active_hand([hand("no_gesture", size=0.3)]) is None


def test_포인터_제스처가_커서를_만든다():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("one", cx=0.5, cy=0.5)]] * 5)
    cur = [e for e in ev if e.type == "cursor"]
    assert cur, "커서 이벤트가 있어야 함"
    assert 0.0 <= cur[-1].x <= 1.0 and 0.0 <= cur[-1].y <= 1.0


def test_좌우반전_매핑():
    gi = GestureInterpreter(GestureConfig(mirror=True, active_region=(0, 0, 1, 1)))
    assert gi.to_screen(0.2, 0.5)[0] == 0.8   # 카메라 왼쪽 = 사용자 화면 오른쪽
    gi2 = GestureInterpreter(GestureConfig(mirror=False, active_region=(0, 0, 1, 1)))
    assert gi2.to_screen(0.2, 0.5)[0] == 0.2


def test_활성영역_밖은_가장자리로_고정():
    gi = GestureInterpreter(GestureConfig(mirror=False))
    assert gi.to_screen(0.0, 0.0) == (0.0, 0.0)
    assert gi.to_screen(1.0, 1.0) == (1.0, 1.0)


def test_순간_오탐은_다수결로_무시():
    gi = GestureInterpreter()
    frames = [[hand("one")]] * 6 + [[hand("like")]] + [[hand("one")]] * 3
    feed(gi, frames)
    assert gi.stable_gesture == "one"


def test_가리키다_주먹이면_클릭():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("one")]] * 8 + [[hand("fist")]] * 4)
    assert "click" in types(ev)


def test_포인터없이_주먹만이면_클릭_아님():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("fist")]] * 15)
    assert "click" not in types(ev)


def test_손바닥_좌우이동은_스와이프():
    gi = GestureInterpreter()
    # 카메라 기준 x 0.7 → 0.3 (dx<0) = 사용자 화면 기준 오른쪽 이동 (mirror)
    xs = [0.7 - 0.04 * i for i in range(11)]
    ev, _ = feed(gi, [[hand("palm", cx=x)] for x in xs])
    sw = [e for e in ev if e.type == "swipe"]
    assert len(sw) == 1 and sw[0].direction == "right"


def test_반대방향_스와이프():
    gi = GestureInterpreter()
    xs = [0.3 + 0.04 * i for i in range(11)]
    ev, _ = feed(gi, [[hand("palm", cx=x)] for x in xs])
    sw = [e for e in ev if e.type == "swipe"]
    assert len(sw) == 1 and sw[0].direction == "left"


def test_손바닥_정지는_스와이프_아님():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("palm", cx=0.5)]] * 30)
    assert "swipe" not in types(ev)


def test_대각선_흔들기는_스와이프_아님():
    gi = GestureInterpreter()
    pts = [(0.3 + 0.04 * i, 0.2 + 0.05 * i) for i in range(11)]
    ev, _ = feed(gi, [[hand("palm", cx=x, cy=y)] for x, y in pts])
    assert "swipe" not in types(ev)


def test_엄지위_유지하면_확인_한번만():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("like")]] * int(FPS * 1.5))
    assert types(ev).count("confirm") == 1
    holds = [e for e in ev if e.type == "hold"]
    assert holds and all(0 <= e.progress < 1 for e in holds)


def test_짧게_보인_엄지는_확인_아님():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("like")]] * int(FPS * 0.3) + [[]] * 5)
    assert "confirm" not in types(ev)


def test_유지명령_매핑():
    for label, cmd in (("dislike", "back"), ("peace", "home")):
        gi = GestureInterpreter()
        ev, _ = feed(gi, [[hand(label)]] * FPS)
        assert cmd in types(ev)


def test_손이_사라지면_hand_lost_한번():
    gi = GestureInterpreter()
    ev, _ = feed(gi, [[hand("one")]] * 5 + [[]] * int(FPS * 2))
    assert types(ev).count("hand_lost") == 1


def test_쿨다운중에는_명령_재발생_없음():
    gi = GestureInterpreter(GestureConfig(cooldown_s=5.0))
    ev, _ = feed(gi, [[hand("like")]] * (FPS * 3))
    assert types(ev).count("confirm") == 1
