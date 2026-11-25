"""HaGRID 변환 스크립트 테스트 (가짜 주석·이미지로)."""

import json

import pytest

from training import prepare_hagrid as ph


def test_박스_변환():
    cx, cy, w, h = ph.hagrid_to_yolo([0.1, 0.2, 0.3, 0.4])
    assert (round(cx, 4), round(cy, 4), w, h) == (0.25, 0.4, 0.3, 0.4)


def test_박스_화면밖_잘라냄():
    cx, cy, w, h = ph.hagrid_to_yolo([0.9, 0.9, 0.3, 0.3])
    assert cx + w / 2 <= 1.0 + 1e-9 and cy + h / 2 <= 1.0 + 1e-9


def test_coco_픽셀변환():
    assert ph.hagrid_to_coco([0.1, 0.2, 0.3, 0.4], 100, 200) == [10.0, 40.0, 30.0, 80.0]


def test_선택안한_클래스와_no_gesture_제외():
    rec = {"bboxes": [[0.1, 0.1, 0.2, 0.2], [0.5, 0.5, 0.2, 0.2], [0.3, 0.3, 0.1, 0.1]],
           "labels": ["one", "no_gesture", "call"]}
    out = ph.convert_record(rec, {"one": 0, "fist": 1}, keep_no_gesture=False)
    assert [c for c, _ in out] == [0]
    out2 = ph.convert_record(rec, {"one": 0, "no_gesture": 1}, keep_no_gesture=True)
    assert [c for c, _ in out2] == [0, 1]


@pytest.fixture
def fake_hagrid(tmp_path):
    from PIL import Image

    ann = tmp_path / "ann" / "train"
    ann.mkdir(parents=True)
    imgs = tmp_path / "images"
    for cls in ("one", "fist"):
        (imgs / cls).mkdir(parents=True)
        data = {}
        for i in range(3):
            iid = f"{cls}_{i}"
            Image.new("RGB", (64, 48)).save(imgs / cls / f"{iid}.jpg")
            data[iid] = {"bboxes": [[0.2, 0.2, 0.3, 0.4]], "labels": [cls]}
        (ann / f"{cls}.json").write_text(json.dumps(data))
    return tmp_path


def test_전체_변환_yolo_coco(fake_hagrid):
    out = fake_hagrid / "out"
    ph.main(["--ann-dir", str(fake_hagrid / "ann"), "--images-root", str(fake_hagrid / "images"),
             "--out", str(out), "--classes", "one", "fist", "--splits", "train",
             "--format", "both", "--copy"])
    labels = list((out / "yolo" / "labels" / "train").glob("*.txt"))
    assert len(labels) == 6
    line = (out / "yolo" / "labels" / "train" / "fist_0.txt").read_text().split()
    assert line[0] == "1"
    coco = json.loads((out / "coco" / "train" / "_annotations.coco.json").read_text())
    assert len(coco["images"]) == 6 and len(coco["annotations"]) == 6
    assert (out / "yolo" / "data.yaml").read_text().count(": ") >= 5


def test_split_구분없는_주석은_사람단위로_겹치지않게_나눔(tmp_path):
    """축소판처럼 <cls>.json 하나만 있을 때: train/val/test 가 겹치지 않고, 같은 사람은 한쪽에만."""
    from PIL import Image

    ann = tmp_path / "ann_train_val"          # split 폴더 없음
    ann.mkdir()
    imgs = tmp_path / "imgs" / "train_val_one"  # 클래스 폴더 이름도 다름 → 색인으로 찾아야 함
    imgs.mkdir(parents=True)
    data = {}
    for i in range(200):
        iid = f"img{i:03d}"
        Image.new("RGB", (32, 32)).save(imgs / f"{iid}.jpg")
        data[iid] = {"bboxes": [[0.2, 0.2, 0.3, 0.3]], "labels": ["one"], "user_id": f"u{i // 4}"}
    (ann / "one.json").write_text(json.dumps(data))

    out = tmp_path / "out"
    ph.main(["--ann-dir", str(tmp_path), "--images-root", str(tmp_path / "imgs"),
             "--out", str(out), "--classes", "one", "--max-per-class", "0", "--copy"])
    names = {s: {p.stem for p in (out / "yolo" / "labels" / s).glob("*.txt")}
             for s in ("train", "val", "test")}
    assert sum(len(v) for v in names.values()) == 200          # 빠짐 없이
    assert not (names["train"] & names["val"]) and not (names["train"] & names["test"])
    assert not (names["val"] & names["test"])
    assert len(names["train"]) > len(names["val"]) > 0          # 대략 8:1:1
    for split, ids in names.items():                            # 같은 사람은 한 split 에만
        users = {data[i]["user_id"] for i in ids}
        for other, oids in names.items():
            if other != split:
                assert not users & {data[i]["user_id"] for i in oids}
