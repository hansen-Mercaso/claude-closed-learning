from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

_SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TEMPLATE_REPO = "git@github.com:hansen-Mercaso/claude-closed-learning.git"


def pick_latest_stable_tag(tags: list[str]) -> str:
    parsed: list[tuple[int, int, int, str]] = []
    for raw in tags:
        tag = raw.strip()
        match = _SEMVER.match(tag)
        if not match:
            continue
        parsed.append((int(match.group(1)), int(match.group(2)), int(match.group(3)), tag))

    if not parsed:
        raise ValueError("no stable semver tag found")

    parsed.sort(key=lambda item: (item[0], item[1], item[2]))
    return parsed[-1][3]


def extract_template_payload(extracted_root: Path) -> Path:
    candidate = extracted_root / "scripts" / "hermes_learning"
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError("template payload missing scripts/hermes_learning")
    return candidate


def list_remote_tags() -> list[str]:
    result = subprocess.run(
        ["git", "ls-remote", "--tags", TEMPLATE_REPO],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"failed to list remote tags: {result.stderr.strip()}")

    tags: list[str] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split("\t", 1)
        if len(parts) != 2:
            continue
        ref = parts[1]
        if not ref.startswith("refs/tags/"):
            continue
        tag = ref.removeprefix("refs/tags/")
        if tag.endswith("^{}"):
            tag = tag[:-3]
        tag = tag.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)

    return tags


def _clone_tag_snapshot(repo: str, tag: str, dst: Path) -> None:
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", tag, repo, str(dst)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"failed to clone tag snapshot: {result.stderr.strip()}")


def resolve_template_source() -> Path:
    tags = list_remote_tags()
    tag = pick_latest_stable_tag(tags)

    temp_root = Path(tempfile.mkdtemp(prefix="hermes-template-"))
    _clone_tag_snapshot(TEMPLATE_REPO, tag, temp_root)

    return extract_template_payload(temp_root)
