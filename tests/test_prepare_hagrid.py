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
