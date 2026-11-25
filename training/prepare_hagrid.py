"""HaGRID 손동작 데이터셋 → YOLO / COCO(RF-DETR) 형식 변환.

HaGRID 주석 형식 (클래스별 JSON, 예: annotations/train/one.json)
    {"<image_id>": {"bboxes": [[x, y, w, h], ...],    # 0~1 정규화, (x, y) = 왼쪽 위
                    "labels": ["one", "no_gesture"],  # 박스마다 클래스
                    ...}}
이미지 위치: <images_root>/<class>/<image_id>.jpg
    (축소판처럼 폴더 구조가 달라도 이미지ID 로 하위 폴더 전체를 찾음)

사용 예 (저장소 루트에서)
    python training/prepare_hagrid.py --ann-dir D:/hagrid/annotations \
        --images-root D:/hagrid/images --out data/processed/hagrid_v1 \
        --classes one fist palm like dislike peace --max-per-class 3000 --format both

결과
    data/processed/hagrid_v1/
        yolo/images/{train,val,test}/*.jpg   yolo/labels/{train,val,test}/*.txt   data.yaml
        coco/{train,valid,test}/*.jpg + _annotations.coco.json            (RF-DETR 형식)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SPLIT_DIRS = {"train": "train", "val": "valid", "test": "test"}  # YOLO 이름 → RF-DETR(COCO) 이름


def hagrid_to_yolo(box: Sequence[float]) -> Tuple[float, float, float, float]:
    """HaGRID [x, y, w, h](왼쪽 위 기준) → YOLO [cx, cy, w, h] (모두 0~1)."""
    x, y, w, h = box
    x = min(max(x, 0.0), 1.0)
    y = min(max(y, 0.0), 1.0)
    w = min(w, 1.0 - x)
    h = min(h, 1.0 - y)
    return (x + w / 2, y + h / 2, w, h)


def hagrid_to_coco(box: Sequence[float], img_w: int, img_h: int) -> List[float]:
    """HaGRID 정규화 박스 → COCO 픽셀 [x, y, w, h]."""
    cx, cy, w, h = hagrid_to_yolo(box)
    return [round((cx - w / 2) * img_w, 2), round((cy - h / 2) * img_h, 2),
            round(w * img_w, 2), round(h * img_h, 2)]


def convert_record(rec: dict, class_to_id: Dict[str, int],
                   keep_no_gesture: bool) -> List[Tuple[int, Tuple[float, float, float, float]]]:
    """주석 1건 → [(class_id, yolo_box), ...]. 선택 안 한 클래스 박스는 버림."""
    out = []
    for box, label in zip(rec.get("bboxes", []), rec.get("labels", [])):
        if label == "no_gesture" and not keep_no_gesture:
            continue
        if label not in class_to_id:
            continue
        yb = hagrid_to_yolo(box)
        if yb[2] <= 0 or yb[3] <= 0:
            continue
        out.append((class_to_id[label], yb))
    return out


IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
_IMAGE_INDEX: Dict[Path, Dict[str, Path]] = {}


def _image_index(images_root: Path) -> Dict[str, Path]:
    """이미지ID → 경로 색인 (폴더를 한 번만 훑음). 이미지마다 rglob 하면 수만 장에서 매우 느림."""
    key = images_root.resolve()
    if key not in _IMAGE_INDEX:
        idx: Dict[str, Path] = {}
        for dirpath, _, files in os.walk(images_root):
            for name in files:
                stem, ext = os.path.splitext(name)
                if ext.lower() in IMAGE_EXTS:
                    idx.setdefault(stem, Path(dirpath) / name)
        _IMAGE_INDEX[key] = idx
    return _IMAGE_INDEX[key]


def find_image(images_root: Path, cls: str, image_id: str) -> Optional[Path]:
    for cand in (images_root / cls / f"{image_id}.jpg", images_root / f"{image_id}.jpg",
                 images_root / cls / f"{image_id}.png"):
        if cand.exists():
            return cand
    return _image_index(images_root).get(image_id)


def assign_split(image_id: str, rec: dict, ratios: Tuple[float, float] = (0.8, 0.1)) -> str:
    """주석이 split 별로 나뉘어 있지 않을 때 직접 나누기.

    같은 사람(user_id)의 사진이 학습과 테스트에 동시에 들어가면 점수가 부풀려지므로
    user_id 해시로 사람 단위로 나눈다 (user_id 가 없으면 이미지ID 로).
    결과가 실행할 때마다 같도록 random 대신 해시를 쓴다.
    """
    key = str(rec.get("user_id") or image_id)
    r = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    if r < ratios[0]:
        return "train"
    return "val" if r < ratios[0] + ratios[1] else "test"


def load_annotations(ann_dir: Path, split: str, cls: str) -> Dict[str, dict]:
    """split 별 주석을 읽는다.

    1) ann_dir/<split>/<cls>.json 또는 ann_dir/<split>_<cls>.json 이 있으면 그대로 사용 (공식판)
    2) 없으면 split 구분 없는 <cls>.json (축소판 등)을 찾아 assign_split 으로 나눠서 사용
    """
    for cand in (ann_dir / split / f"{cls}.json", ann_dir / f"{split}_{cls}.json"):
        if cand.exists():
            with open(cand, encoding="utf-8") as f:
                return json.load(f)
    cand = ann_dir / f"{cls}.json"
    if not cand.exists():
        hits = sorted(ann_dir.rglob(f"{cls}.json"))
        cand = hits[0] if hits else None
    if cand is None:
        print(f"⚠️  {cls}.json 주석 파일을 찾지 못했습니다 → --ann-dir 경로를 확인하세요")
        return {}
    with open(cand, encoding="utf-8") as f:
        data = json.load(f)
    picked = {k: v for k, v in data.items() if assign_split(k, v) == split}
    if not picked:
        print(f"⚠️  {split}/{cls}: 사람 단위로 나눈 결과 0장 (데이터가 너무 적은 경우)")
    return picked


def build_split(ann_dir: Path, split: str, classes: Sequence[str], max_per_class: int,
                seed: int) -> List[Tuple[str, str, dict]]:
    """[(class, image_id, record)] — 클래스별 최대 max_per_class 개 무작위 추출."""
    rng = random.Random(seed)
    items = []
    for cls in classes:
        if cls == "no_gesture":
            continue
        ann = load_annotations(ann_dir, split, cls)
        keys = sorted(ann.keys())
        rng.shuffle(keys)
        if max_per_class > 0:
            keys = keys[:max_per_class]
        items += [(cls, k, ann[k]) for k in keys]
    return items


def write_yolo(items, images_root: Path, out: Path, split: str, class_to_id, keep_no_gesture,
               copy: bool) -> int:
    img_dir = out / "yolo" / "images" / split
    lbl_dir = out / "yolo" / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for cls, image_id, rec in items:
        src = find_image(images_root, cls, image_id)
        if src is None:
            continue
        labels = convert_record(rec, class_to_id, keep_no_gesture)
        if not labels:
            continue
        dst = img_dir / f"{image_id}{src.suffix}"
        _place(src, dst, copy)
        with open(lbl_dir / f"{image_id}.txt", "w", encoding="utf-8") as f:
            for cid, (cx, cy, w, h) in labels:
                f.write(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
        n += 1
    return n


def write_coco(items, images_root: Path, out: Path, split: str, classes, class_to_id,
               keep_no_gesture, copy: bool) -> int:
    from PIL import Image

    d = out / "coco" / SPLIT_DIRS[split]
    d.mkdir(parents=True, exist_ok=True)
    coco = {"images": [], "annotations": [],
            "categories": [{"id": i, "name": c, "supercategory": "hand"}
                           for i, c in enumerate(classes)]}
    ann_id = 0
    for img_id, (cls, image_id, rec) in enumerate(items):
        src = find_image(images_root, cls, image_id)
        if src is None:
            continue
        labels = convert_record(rec, class_to_id, keep_no_gesture)
        if not labels:
            continue
        with Image.open(src) as im:
            w, h = im.size
        fname = f"{image_id}{src.suffix}"
        _place(src, d / fname, copy)
        coco["images"].append({"id": img_id, "file_name": fname, "width": w, "height": h})
        for box, label in zip(rec["bboxes"], rec["labels"]):
            if label not in class_to_id or (label == "no_gesture" and not keep_no_gesture):
                continue
            bb = hagrid_to_coco(box, w, h)
            coco["annotations"].append({"id": ann_id, "image_id": img_id,
                                        "category_id": class_to_id[label], "bbox": bb,
                                        "area": bb[2] * bb[3], "iscrowd": 0})
            ann_id += 1
    with open(d / "_annotations.coco.json", "w", encoding="utf-8") as f:
        json.dump(coco, f, ensure_ascii=False)
    return len(coco["images"])


def write_data_yaml(out: Path, classes: Sequence[str]) -> Path:
    p = out / "yolo" / "data.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"path: {(out / 'yolo').resolve().as_posix()}", "train: images/train",
             "val: images/val", "test: images/test", "names:"]
    lines += [f"  {i}: {c}" for i, c in enumerate(classes)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _place(src: Path, dst: Path, copy: bool) -> None:
    if dst.exists():
        return
    if copy:
        shutil.copy2(src, dst)
    else:
        try:
            dst.symlink_to(src.resolve())
        except OSError:  # Windows 에서 심볼릭 링크 권한이 없으면 복사
            shutil.copy2(src, dst)


def main(argv: Optional[Iterable[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="HaGRID → YOLO / COCO 변환")
    ap.add_argument("--ann-dir", required=True, type=Path)
    ap.add_argument("--images-root", required=True, type=Path)
    ap.add_argument("--out", default=Path("data/processed/hagrid_v1"), type=Path)
    ap.add_argument("--classes", nargs="+",
                    default=["one", "fist", "palm", "like", "dislike", "peace"])
    ap.add_argument("--keep-no-gesture", action="store_true",
                    help="no_gesture(제스처 아닌 손) 박스도 클래스로 학습 → 오탐 감소용")
    ap.add_argument("--max-per-class", type=int, default=3000, help="0 = 전부")
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    ap.add_argument("--format", choices=["yolo", "coco", "both"], default="yolo")
    ap.add_argument("--copy", action="store_true", help="심볼릭 링크 대신 복사")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    classes = list(args.classes)
    if args.keep_no_gesture and "no_gesture" not in classes:
        classes.append("no_gesture")
    class_to_id = {c: i for i, c in enumerate(classes)}
    for split in args.splits:
        # 검증·테스트는 학습의 1/5 만 사용 (시간 절약)
        # (--max-per-class 0 = 전부 → 검증·테스트도 전부)
        cap = args.max_per_class
        if split != "train" and cap > 0:
            cap = max(1, cap // 5)
        items = build_split(args.ann_dir, split, classes, cap, args.seed)
        if split == "train" and not items:
            raise SystemExit("❌ 학습(train) 데이터가 0장입니다. --ann-dir / --images-root 경로를"
                             " 확인하세요. (one.json 등이 들어 있는 폴더가 --ann-dir)")
        if args.format in ("yolo", "both"):
            n = write_yolo(items, args.images_root, args.out, split, class_to_id,
                           args.keep_no_gesture, args.copy)
            print(f"[YOLO] {split}: {n}장")
        if args.format in ("coco", "both"):
            n = write_coco(items, args.images_root, args.out, split, classes, class_to_id,
                           args.keep_no_gesture, args.copy)
            print(f"[COCO] {SPLIT_DIRS[split]}: {n}장")
    if args.format in ("yolo", "both"):
        print("data.yaml →", write_data_yaml(args.out, classes))


if __name__ == "__main__":
    main()
