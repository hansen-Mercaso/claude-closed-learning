from scripts.hermes_learning.approval_executor import parse_approval


def test_parse_pass_subset():
    r = parse_approval("1,2通过")
    assert r["approve"] == [1, 2]


def test_parse_pass_all():
    r = parse_approval("全部通过")
    assert r["approve_all"] is True


def test_parse_edit_and_reject():
    r = parse_approval("1改成:abc\n2拒绝")
    assert r["edits"][1] == "abc"
    assert r["reject"] == [2]


def test_parse_later():
    r = parse_approval("稍后")
    assert r["later"] is True
