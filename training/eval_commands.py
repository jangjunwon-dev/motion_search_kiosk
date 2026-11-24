"""명령 단위 성능평가 — "탐지가 잘 되는가"가 아니라 "키오스크 명령이 의도대로 실행되는가".

방법
  1) 시나리오 파일(예: training/scenarios/basic.txt)에 사용자가 할 동작 순서를 적는다.
       click, swipe_left, swipe_left, click, confirm, back, home ...
  2) 키오스크를 실행한 상태에서 시나리오대로 손동작을 한다 → logs/events_*.csv 가 생김
  3) 비교:
       python training/eval_commands.py --scenario training/scenarios/basic.txt \
           --log logs/events_20261210_141500.csv

출력: 정확 인식 / 누락(동작했는데 안 먹힘) / 오인식(다른 명령으로 인식) / 오발동(안 했는데 실행됨)
      → 명령 인식률 = 정확 / 시나리오 길이,  오발동률 = 오발동 / 실행된 명령 수
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
from pathlib import Path
from typing import Dict, List


def load_scenario(path: Path) -> List[str]:
    cmds: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0]
        cmds += [c.strip() for c in line.replace(",", " ").split() if c.strip()]
    return cmds


def load_log(path: Path) -> List[str]:
    out: List[str] = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row["type"]
            if t == "swipe":
                t = f"swipe_{row['direction']}"
            if t in ("hand_lost", "status"):
                continue
            out.append(t)
    return out


def compare(expected: List[str], actual: List[str]) -> Dict[str, object]:
    """두 명령 순서를 정렬(diff)해서 오류 종류별로 센다."""
    sm = difflib.SequenceMatcher(a=expected, b=actual, autojunk=False)
    correct = missed = wrong = false_trigger = 0
    details = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            correct += i2 - i1
        elif op == "delete":
            missed += i2 - i1
            details += [f"누락: {c}" for c in expected[i1:i2]]
        elif op == "insert":
            false_trigger += j2 - j1
            details += [f"오발동: {c}" for c in actual[j1:j2]]
        else:  # replace
            k = min(i2 - i1, j2 - j1)
            wrong += k
            pairs = zip(expected[i1:i1 + k], actual[j1:j1 + k])
            details += [f"오인식: {e} → {a}" for e, a in pairs]
            missed += (i2 - i1) - k
            false_trigger += (j2 - j1) - k
    n = len(expected) or 1
    m = len(actual) or 1
    return {"scenario_len": len(expected), "executed": len(actual), "correct": correct,
            "missed": missed, "wrong": wrong, "false_trigger": false_trigger,
            "command_accuracy": round(correct / n, 4),
            "false_trigger_rate": round(false_trigger / m, 4), "details": details}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, type=Path)
    ap.add_argument("--log", required=True, type=Path)
    args = ap.parse_args()
    res = compare(load_scenario(args.scenario), load_log(args.log))
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
