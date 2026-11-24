from training.eval_commands import compare


def test_완벽_일치():
    r = compare(["click", "confirm"], ["click", "confirm"])
    assert r["command_accuracy"] == 1.0 and r["false_trigger"] == 0


def test_누락_오인식_오발동():
    exp = ["click", "swipe_left", "confirm", "back"]
    act = ["click", "swipe_right", "confirm", "home", "back"]
    r = compare(exp, act)
    assert r["correct"] == 3
    assert r["wrong"] == 1          # swipe_left → swipe_right
    assert r["false_trigger"] == 1  # home
    assert r["missed"] == 0
