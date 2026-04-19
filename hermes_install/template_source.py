from __future__ import annotations

import json
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path

_SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TEMPLATE_REPO = "https://github.com/hansen-Mercaso/claude-closed-learning"
_DEFAULT_TAGS_API_URL = "https://api.github.com/repos/hansen-Mercaso/claude-closed-learning/tags?per_page=200"


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


def list_remote_tags(repo_api_tags_url: str | None = None) -> list[str]:
    url = repo_api_tags_url or _DEFAULT_TAGS_API_URL
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if not isinstance(payload, list):
        return []

    return [str(item.get("name", "")).strip() for item in payload if isinstance(item, dict)]


def resolve_template_source() -> Path:
    tags = list_remote_tags()
    tag = pick_latest_stable_tag(tags)

    temp_root = Path(tempfile.mkdtemp(prefix="hermes-template-"))
    temp_root.mkdir(parents=True, exist_ok=True)

    archive_path = temp_root / f"{tag}.zip"
    archive_url = f"{TEMPLATE_REPO}/archive/refs/tags/{tag}.zip"
    urllib.request.urlretrieve(archive_url, archive_path)

    extract_root = temp_root / "extract"
    shutil.unpack_archive(str(archive_path), str(extract_root))

    children = [path for path in extract_root.iterdir() if path.is_dir()]
    if len(children) != 1:
        raise ValueError("unexpected template archive structure")

    return extract_template_payload(children[0])
