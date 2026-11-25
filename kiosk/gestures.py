"""손동작 탐지 결과(바운딩 박스) → 키오스크 명령으로 바꾸는 순수 로직.

이 모듈은 카메라·모델·웹서버에 의존하지 않습니다. (pytest 로 단독 테스트 가능)

흐름 (프레임마다 update() 1회 호출)
    1) 활성 손 고르기   : 일정 크기 이상인 손 중 가장 큰 것 = 키오스크 앞에 선 사용자
    2) 제스처 안정화    : 최근 N프레임 다수결 → 순간 오탐(깜빡임) 제거
    3) 커서 계산        : 'one'(검지) 박스 위쪽 중앙 → 화면 좌표, 좌우 반전 + EMA 평활화
    4) 명령 판정        : 클릭(one→fist), 스와이프(palm 좌우 이동),
                          유지형 명령(like=확인, dislike=뒤로, peace=홈)
    5) 쿨다운           : 명령 직후 일정 시간 같은 명령 재발생 차단
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple


@dataclass
class Detection:
    """탐지기 1개 결과. 좌표는 0~1 로 정규화된 (x1, y1, x2, y2)."""

    label: str
    conf: float
    box: Tuple[float, float, float, float]

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.box
        return ((x1 + x2) / 2, (y1 + y2) / 2)


def iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    """두 박스의 겹침 정도 (Intersection over Union, 0~1)."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass
class GestureConfig:
    """제스처 해석 파라미터. configs/app.yaml 의 gesture 항목과 1:1 대응."""

    min_conf: float = 0.5            # 이보다 낮은 신뢰도 탐지는 버림
    min_hand_area: float = 0.004     # 화면 대비 손 박스 면적 — 멀리 지나가는 사람 무시
    vote_window: int = 5             # 다수결에 쓰는 최근 프레임 수
    vote_min: int = 3                # 다수결 최소 득표
    cursor_alpha: float = 0.35       # EMA 평활화 계수 (클수록 반응 빠르고 떨림 큼)
    active_region: Tuple[float, float, float, float] = (0.15, 0.10, 0.85, 0.80)
    mirror: bool = True              # 셀피 카메라 → 좌우 반전해야 손 방향과 커서 방향 일치
    click_window_s: float = 0.8      # one → fist 전환이 이 시간 안에 일어나면 클릭
    swipe_window_s: float = 0.45     # 스와이프 판정 구간
    swipe_min_dx: float = 0.18       # 구간 내 손바닥 중심 x 이동량 (정규화)
    swipe_max_dy: float = 0.12       # 세로 흔들림 허용치
    hold_s: float = 0.7              # like/dislike/peace 를 이만큼 유지해야 명령
    cooldown_s: float = 0.9          # 명령 직후 재발생 차단 시간
    lost_after_s: float = 1.0        # 손이 안 보인 지 이 시간이 지나면 hand_lost
    same_hand_iou: float = 0.5       # 이만큼 겹치는 박스는 같은 손으로 보고 신뢰도 높은 쪽 선택
    # 제스처 클래스 → 역할 (모델 클래스 이름이 달라도 여기서 맞춤)
    pointer_labels: Tuple[str, ...] = ("one", "point")
    grab_labels: Tuple[str, ...] = ("fist", "grabbing", "grip")
    swipe_labels: Tuple[str, ...] = ("palm", "stop")
    hold_commands: dict = field(default_factory=lambda: {
        "like": "confirm",
        "dislike": "back",
        "peace": "home",
    })


@dataclass
class KioskEvent:
    """웹 화면으로 보내는 이벤트. to_dict() 결과가 WebSocket JSON 이 됨."""

    type: str                       # cursor / click / swipe / confirm / back / home / hand_lost
    x: Optional[float] = None
    y: Optional[float] = None
    direction: Optional[str] = None  # swipe: left / right
    gesture: Optional[str] = None
    conf: Optional[float] = None
    progress: Optional[float] = None  # 유지형 명령 진행률 0~1 (화면 게이지용)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class GestureInterpreter:
    """프레임 단위 탐지 결과를 받아 키오스크 이벤트 목록을 돌려준다."""

    def __init__(self, cfg: Optional[GestureConfig] = None) -> None:
        self.cfg = cfg or GestureConfig()
        self._votes: Deque[str] = deque(maxlen=self.cfg.vote_window)
        self._cursor: Optional[Tuple[float, float]] = None
        self._palm_track: Deque[Tuple[float, float, float]] = deque()  # (t, x, y)
        self._last_pointer_t: Optional[float] = None
        self._hold_label: Optional[str] = None
        self._hold_start: float = 0.0
        self._cooldown_until: float = 0.0
        self._last_seen_t: Optional[float] = None
        self._lost_sent = True
        self.stable_gesture: Optional[str] = None

    # ------------------------------------------------------------------ 공개 API
    def update(self, detections: List[Detection], t: float) -> List[KioskEvent]:
        """t: 현재 시각(초, 단조 증가). 반환: 이번 프레임에 발생한 이벤트들."""
        events: List[KioskEvent] = []
        hand = self.select_active_hand(detections)

        if hand is None:
            self._votes.append("none")
            self._palm_track.clear()
            self._hold_label = None
            if (self._last_seen_t is not None and not self._lost_sent
                    and t - self._last_seen_t >= self.cfg.lost_after_s):
                self._lost_sent = True
                self._cursor = None
                self.stable_gesture = None
                events.append(KioskEvent("hand_lost"))
            return events

        self._last_seen_t = t
        self._lost_sent = False
        self._votes.append(hand.label)
        gesture = self._vote()
        prev = self.stable_gesture
        self.stable_gesture = gesture

        # 커서: 포인터 제스처일 때만 움직임 (주먹 쥘 때 커서가 튀는 것 방지)
        if gesture in self.cfg.pointer_labels:
            self._last_pointer_t = t
            cx, cy = self._update_cursor(hand)
            events.append(KioskEvent("cursor", x=cx, y=cy, gesture=gesture,
                                     conf=round(hand.conf, 3)))

        if t < self._cooldown_until:
            return events

        # 클릭: 직전까지 포인터였다가 주먹으로 바뀌면
        if (gesture in self.cfg.grab_labels and prev in self.cfg.pointer_labels
                and self._last_pointer_t is not None
                and t - self._last_pointer_t <= self.cfg.click_window_s
                and self._cursor is not None):
            events.append(KioskEvent("click", x=self._cursor[0], y=self._cursor[1],
                                     gesture=gesture))
            self._start_cooldown(t)
            return events

        # 스와이프: 손바닥 중심의 가로 이동
        swipe = self._check_swipe(hand, gesture, t)
        if swipe:
            events.append(KioskEvent("swipe", direction=swipe, gesture=gesture))
            self._start_cooldown(t)
            return events

        # 유지형 명령
        hold_evt = self._check_hold(gesture, t)
        if hold_evt:
            events.append(hold_evt)
        return events

    def select_active_hand(self, detections: List[Detection]) -> Optional[Detection]:
        """신뢰도·크기 조건을 통과한 손 중 가장 큰 것(가장 가까운 사용자).

        같은 손에 클래스만 다른 박스가 겹쳐 나오는 경우가 있음 (예: palm 0.45 + like 0.44,
        손 모양이 바뀌는 순간에 특히 많음). 크기만 보면 매 프레임 라벨이 바뀌어 깜빡이므로,
        가장 큰 손과 많이 겹치는(IoU ≥ same_hand_iou) 박스들 중에서는 신뢰도가 가장 높은 것을 고른다.
        """
        cands = [d for d in detections
                 if d.conf >= self.cfg.min_conf and d.area >= self.cfg.min_hand_area
                 and d.label != "no_gesture"]
        if not cands:
            return None
        biggest = max(cands, key=lambda d: d.area)
        same_hand = [d for d in cands if iou(d.box, biggest.box) >= self.cfg.same_hand_iou]
        return max(same_hand, key=lambda d: d.conf)

    # ------------------------------------------------------------------ 내부 로직
    def _vote(self) -> Optional[str]:
        label, count = Counter(self._votes).most_common(1)[0]
        if label == "none" or count < min(self.cfg.vote_min, len(self._votes)):
            return self.stable_gesture if label != "none" else None
        return label

    def to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """카메라 정규화 좌표 → 화면 정규화 좌표 (활성 영역 확대 + 좌우 반전)."""
        ax1, ay1, ax2, ay2 = self.cfg.active_region
        sx = (x - ax1) / (ax2 - ax1)
        sy = (y - ay1) / (ay2 - ay1)
        if self.cfg.mirror:
            sx = 1.0 - sx
        return (min(1.0, max(0.0, sx)), min(1.0, max(0.0, sy)))

    def _update_cursor(self, hand: Detection) -> Tuple[float, float]:
        x1, y1, x2, y2 = hand.box
        # 검지 끝은 박스 위쪽에 있으므로 위쪽 20% 지점을 포인터로 사용
        tip = ((x1 + x2) / 2, y1 + 0.2 * (y2 - y1))
        target = self.to_screen(*tip)
        if self._cursor is None:
            self._cursor = target
        else:
            a = self.cfg.cursor_alpha
            self._cursor = (a * target[0] + (1 - a) * self._cursor[0],
                            a * target[1] + (1 - a) * self._cursor[1])
        return (round(self._cursor[0], 4), round(self._cursor[1], 4))

    def _check_swipe(self, hand: Detection, gesture: Optional[str], t: float) -> Optional[str]:
        if gesture not in self.cfg.swipe_labels:
            self._palm_track.clear()
            return None
        cx, cy = hand.center
        self._palm_track.append((t, cx, cy))
        while self._palm_track and t - self._palm_track[0][0] > self.cfg.swipe_window_s:
            self._palm_track.popleft()
        if len(self._palm_track) < 3:
            return None
        xs = [p[1] for p in self._palm_track]
        ys = [p[2] for p in self._palm_track]
        dx = xs[-1] - xs[0]
        if abs(dx) >= self.cfg.swipe_min_dx and max(ys) - min(ys) <= self.cfg.swipe_max_dy:
            self._palm_track.clear()
            # 반환값 = 사용자가 보는 화면 기준으로 손이 움직인 방향.
            # 셀피 카메라 원본에서 x 감소(dx<0) = 사용자 기준 오른쪽 이동 (거울 반전)
            moved_right_on_screen = (dx < 0) if self.cfg.mirror else (dx > 0)
            # 화면(web/app.js)에서는 left = 다음 페이지, right = 이전 페이지 (스마트폰과 동일)
            return "right" if moved_right_on_screen else "left"
        return None

    def _check_hold(self, gesture: Optional[str], t: float) -> Optional[KioskEvent]:
        cmd = self.cfg.hold_commands.get(gesture or "")
        if cmd is None:
            self._hold_label = None
            return None
        if self._hold_label != gesture:
            self._hold_label = gesture
            self._hold_start = t
        progress = (t - self._hold_start) / self.cfg.hold_s
        if progress >= 1.0:
            self._hold_label = None
            self._start_cooldown(t)
            return KioskEvent(cmd, gesture=gesture, progress=1.0)
        return KioskEvent("hold", gesture=gesture, progress=round(progress, 3))

    def _start_cooldown(self, t: float) -> None:
        self._cooldown_until = t + self.cfg.cooldown_s
        self._palm_track.clear()
        self._hold_label = None
