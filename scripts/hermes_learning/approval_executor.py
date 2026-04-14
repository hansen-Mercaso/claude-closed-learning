from __future__ import annotations

import re


def _nums(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s)]


def parse_approval(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    result = {
        "approve": [],
        "approve_all": False,
        "reject": [],
        "edits": {},
        "later": False,
    }
    if any("稍后" in l for l in lines) or text.strip() == "":
        result["later"] = True
        return result

    if any("全部通过" in l for l in lines):
        result["approve_all"] = True

    for l in lines:
        if "改成:" in l:
            left, right = l.split("改成:", 1)
            ns = _nums(left)
            if ns:
                result["edits"][ns[0]] = right.strip()
        elif "拒绝" in l:
            result["reject"].extend(_nums(l))
        elif "通过" in l and "全部" not in l:
            result["approve"].extend(_nums(l))

    result["approve"] = sorted(set(result["approve"]))
    result["reject"] = sorted(set(result["reject"]))
    return result
