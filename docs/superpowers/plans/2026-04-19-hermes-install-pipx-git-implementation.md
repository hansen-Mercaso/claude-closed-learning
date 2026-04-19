# Hermes Install (pipx + Git) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pipx-installable `hermes-install` command that provides GUI folder selection + GUI preview confirmation and installs Hermes Learning into a selected repository on macOS/Windows.

**Architecture:** Add a new `hermes_install` package responsible for tag resolution, template download, GUI interaction, and orchestration. Reuse existing migration core (`scripts/hermes_learning/migrate.py`) for plan/apply logic, with a small adapter for source-root-based execution and non-git target auto-init. Keep GUI code isolated from migration logic so integration tests can run headless.

**Tech Stack:** Python 3.11+, pathlib, argparse, tkinter, subprocess, urllib/json, tarfile/zipfile, pytest, pipx packaging via `pyproject.toml`.

---

## File Structure (what to touch and why)

- Create: `.worktrees/hermes-learning/pyproject.toml`
  - Define package metadata and script entrypoint `hermes-install`.

- Create: `.worktrees/hermes-learning/hermes_install/__init__.py`
  - Package marker.

- Create: `.worktrees/hermes-learning/hermes_install/cli.py`
  - Top-level installer orchestration entrypoint.

- Create: `.worktrees/hermes-learning/hermes_install/template_source.py`
  - Resolve latest stable tag and download/extract template snapshot.

- Create: `.worktrees/hermes-learning/hermes_install/ui.py`
  - GUI folder picker + preview/confirm + message dialogs (tkinter).

- Create: `.worktrees/hermes-learning/hermes_install/migrator.py`
  - Adapter to invoke migration plan/apply using extracted template source.

- Modify: `.worktrees/hermes-learning/scripts/hermes_learning/migrate.py`
  - Add small reusable helper for non-CLI callers (source-root + auto-init behavior).

- Create: `.worktrees/hermes-learning/tests/hermes_install/test_template_source.py`
  - Unit tests for semver tag parsing and selection.

- Create: `.worktrees/hermes-learning/tests/hermes_install/test_migrator.py`
  - Integration-style tests for auto-init + migration wiring without GUI.

- Create: `.worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py`
  - CLI orchestration tests with mocked UI/template source.

---

### Task 1: Package the installer command for pipx

**Files:**
- Create: `.worktrees/hermes-learning/pyproject.toml`
- Create: `.worktrees/hermes-learning/hermes_install/__init__.py`
- Create: `.worktrees/hermes-learning/hermes_install/cli.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py
from __future__ import annotations

import importlib


def test_cli_module_exposes_main_callable():
    mod = importlib.import_module("hermes_install.cli")
    assert callable(mod.main)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_cli_module_exposes_main_callable -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'hermes_install'`)

- [ ] **Step 3: Write minimal implementation**

```python
# .worktrees/hermes-learning/hermes_install/__init__.py
"""Hermes installer package."""
```

```python
# .worktrees/hermes-learning/hermes_install/cli.py
from __future__ import annotations


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```toml
# .worktrees/hermes-learning/pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-install"
version = "0.1.0"
description = "Hermes Learning installer"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
hermes-install = "hermes_install.cli:main"

[tool.setuptools]
packages = ["hermes_install"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_cli_module_exposes_main_callable -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add pyproject.toml hermes_install/__init__.py hermes_install/cli.py tests/hermes_install/test_cli_flow.py
git -C .worktrees/hermes-learning commit -m "feat: scaffold hermes-install package and entrypoint"
```

---

### Task 2: Implement latest stable tag selection rules

**Files:**
- Create: `.worktrees/hermes-learning/hermes_install/template_source.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_template_source.py`

- [ ] **Step 1: Write the failing test**

```python
# .worktrees/hermes-learning/tests/hermes_install/test_template_source.py
from __future__ import annotations

import pytest

from hermes_install.template_source import pick_latest_stable_tag


def test_pick_latest_stable_tag_prefers_highest_semver():
    tags = ["v0.1.0", "v0.2.0", "v0.10.0", "v0.10.0-rc.1", "not-a-version"]
    assert pick_latest_stable_tag(tags) == "v0.10.0"


def test_pick_latest_stable_tag_raises_when_no_stable_tags():
    tags = ["v0.2.0-rc.1", "snapshot", "foo"]
    with pytest.raises(ValueError, match="no stable semver tag"):
        pick_latest_stable_tag(tags)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_template_source.py::test_pick_latest_stable_tag_prefers_highest_semver .worktrees/hermes-learning/tests/hermes_install/test_template_source.py::test_pick_latest_stable_tag_raises_when_no_stable_tags -q`
Expected: FAIL (`ModuleNotFoundError` or `ImportError`)

- [ ] **Step 3: Write minimal implementation**

```python
# .worktrees/hermes-learning/hermes_install/template_source.py
from __future__ import annotations

import re

_SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def pick_latest_stable_tag(tags: list[str]) -> str:
    parsed: list[tuple[int, int, int, str]] = []
    for raw in tags:
        m = _SEMVER.match(raw.strip())
        if not m:
            continue
        major, minor, patch = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        parsed.append((major, minor, patch, raw.strip()))

    if not parsed:
        raise ValueError("no stable semver tag found")

    parsed.sort(key=lambda x: (x[0], x[1], x[2]))
    return parsed[-1][3]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_template_source.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add hermes_install/template_source.py tests/hermes_install/test_template_source.py
git -C .worktrees/hermes-learning commit -m "feat: add stable semver tag selection for installer"
```

---

### Task 3: Add template fetch + extract from repository tag

**Files:**
- Modify: `.worktrees/hermes-learning/hermes_install/template_source.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_template_source.py`

- [ ] **Step 1: Write the failing test**

```python
# append in .worktrees/hermes-learning/tests/hermes_install/test_template_source.py
from pathlib import Path

from hermes_install import template_source


def test_extract_template_payload_returns_hermes_learning_root(tmp_path: Path):
    bundle = tmp_path / "bundle"
    root = bundle / "repo-v0.1.0" / "scripts" / "hermes_learning"
    root.mkdir(parents=True)
    (root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    out = template_source.extract_template_payload(bundle / "repo-v0.1.0")

    assert out == root
    assert (out / "migrate.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_template_source.py::test_extract_template_payload_returns_hermes_learning_root -q`
Expected: FAIL (`extract_template_payload` missing)

- [ ] **Step 3: Write minimal implementation**

```python
# append in .worktrees/hermes-learning/hermes_install/template_source.py
from pathlib import Path


def extract_template_payload(extracted_root: Path) -> Path:
    candidate = extracted_root / "scripts" / "hermes_learning"
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError("template payload missing scripts/hermes_learning")
    return candidate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_template_source.py::test_extract_template_payload_returns_hermes_learning_root -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add hermes_install/template_source.py tests/hermes_install/test_template_source.py
git -C .worktrees/hermes-learning commit -m "feat: add template payload extraction helper"
```

---

### Task 4: Build migration adapter with auto git init

**Files:**
- Create: `.worktrees/hermes-learning/hermes_install/migrator.py`
- Modify: `.worktrees/hermes-learning/scripts/hermes_learning/migrate.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_migrator.py`

- [ ] **Step 1: Write the failing test**

```python
# .worktrees/hermes-learning/tests/hermes_install/test_migrator.py
from __future__ import annotations

import subprocess
from pathlib import Path

from hermes_install.migrator import ensure_git_repo, preview_install


def test_ensure_git_repo_auto_inits_non_repo(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    ensure_git_repo(target)

    probe = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0
    assert probe.stdout.strip() == "true"


def test_preview_install_returns_plan_with_settings_change(tmp_path: Path):
    source_root = tmp_path / "template" / "scripts" / "hermes_learning"
    target = tmp_path / "target"
    source_root.mkdir(parents=True)
    (source_root / "migrate.py").write_text("# ok\n", encoding="utf-8")
    target.mkdir()

    ensure_git_repo(target)
    out = preview_install(source_root=source_root, target_repo=target)

    assert out["ok"] is True
    assert "plan" in out
    assert "settings_change" in out["plan"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_migrator.py -q`
Expected: FAIL (`hermes_install.migrator` missing)

- [ ] **Step 3: Write minimal implementation**

```python
# .worktrees/hermes-learning/hermes_install/migrator.py
from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.hermes_learning import migrate


def ensure_git_repo(target_repo: Path) -> None:
    target_repo.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        ["git", "-C", str(target_repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode == 0 and probe.stdout.strip() == "true":
        return

    init = subprocess.run(["git", "-C", str(target_repo), "init"], capture_output=True, text=True, check=False)
    if init.returncode != 0:
        raise ValueError(f"failed to initialize git repository: {init.stderr.strip()}")


def preview_install(*, source_root: Path, target_repo: Path) -> dict:
    plan = migrate.build_migration_plan(source_root=source_root, target_repo=target_repo)
    report = migrate.render_preview(plan)
    return {"ok": True, "plan": plan, "report": report}


def apply_install(*, source_root: Path, target_repo: Path, force: bool = False) -> dict:
    plan = migrate.build_migration_plan(source_root=source_root, target_repo=target_repo)
    return migrate.apply_migration(plan=plan, source_root=source_root, target_repo=target_repo, force=force)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_migrator.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add hermes_install/migrator.py tests/hermes_install/test_migrator.py
git -C .worktrees/hermes-learning commit -m "feat: add installer migration adapter with auto git init"
```

---

### Task 5: Add GUI layer for folder pick + preview confirm

**Files:**
- Create: `.worktrees/hermes-learning/hermes_install/ui.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# append in .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py
from hermes_install import ui


def test_preview_summary_includes_conflict_and_settings_status():
    plan = {
        "file_changes": [
            {"type": "add", "rel": "hooks/stop-hook.sh"},
            {"type": "conflict", "rel": "mcp/server.py"},
            {"type": "skip", "rel": "state.py"},
        ],
        "settings_change": {"changed": True},
    }

    text = ui.build_preview_summary(plan)

    assert "新增: 1" in text
    assert "冲突: 1" in text
    assert "跳过: 1" in text
    assert "settings 变更: 是" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_preview_summary_includes_conflict_and_settings_status -q`
Expected: FAIL (`ui` module missing)

- [ ] **Step 3: Write minimal implementation**

```python
# .worktrees/hermes-learning/hermes_install/ui.py
from __future__ import annotations

from collections import Counter


def build_preview_summary(plan: dict) -> str:
    changes = plan.get("file_changes", [])
    counts = Counter(item.get("type") for item in changes)
    settings_changed = bool(plan.get("settings_change", {}).get("changed"))

    return "\n".join(
        [
            "Hermes 安装预览",
            f"新增: {counts.get('add', 0)}",
            f"冲突: {counts.get('conflict', 0)}",
            f"跳过: {counts.get('skip', 0)}",
            f"settings 变更: {'是' if settings_changed else '否'}",
        ]
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_preview_summary_includes_conflict_and_settings_status -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add hermes_install/ui.py tests/hermes_install/test_cli_flow.py
git -C .worktrees/hermes-learning commit -m "feat: add preview summary builder for installer UI"
```

---

### Task 6: Wire end-to-end installer flow in cli.main

**Files:**
- Modify: `.worktrees/hermes-learning/hermes_install/cli.py`
- Modify: `.worktrees/hermes-learning/hermes_install/ui.py`
- Modify: `.worktrees/hermes-learning/hermes_install/template_source.py`
- Modify: `.worktrees/hermes-learning/hermes_install/migrator.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# append in .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py
from pathlib import Path

from hermes_install import cli


class _FakeUI:
    def __init__(self, target: Path, confirmed: bool):
        self.target = target
        self.confirmed = confirmed
        self.messages = []

    def choose_target_directory(self):
        return self.target

    def confirm_preview(self, summary: str) -> bool:
        self.messages.append(summary)
        return self.confirmed

    def show_info(self, title: str, message: str) -> None:
        self.messages.append(f"INFO:{title}:{message}")

    def show_error(self, title: str, message: str) -> None:
        self.messages.append(f"ERROR:{title}:{message}")


def test_main_applies_when_user_confirms(tmp_path: Path, monkeypatch):
    template_root = tmp_path / "template" / "scripts" / "hermes_learning"
    template_root.mkdir(parents=True)
    (template_root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    target = tmp_path / "target"
    ui = _FakeUI(target=target, confirmed=True)

    monkeypatch.setattr(cli, "resolve_template_source", lambda: template_root)
    monkeypatch.setattr(cli, "ui", ui)

    rc = cli.main()

    assert rc == 0
    assert (target / ".claude" / "settings.json").exists()


def test_main_returns_nonzero_when_user_cancels(tmp_path: Path, monkeypatch):
    template_root = tmp_path / "template" / "scripts" / "hermes_learning"
    template_root.mkdir(parents=True)
    (template_root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    target = tmp_path / "target"
    ui = _FakeUI(target=target, confirmed=False)

    monkeypatch.setattr(cli, "resolve_template_source", lambda: template_root)
    monkeypatch.setattr(cli, "ui", ui)

    rc = cli.main()

    assert rc == 1
    assert not (target / ".claude" / "settings.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_main_applies_when_user_confirms .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_main_returns_nonzero_when_user_cancels -q`
Expected: FAIL (main still returns static 0)

- [ ] **Step 3: Write minimal implementation**

```python
# .worktrees/hermes-learning/hermes_install/cli.py
from __future__ import annotations

from pathlib import Path

from hermes_install import ui
from hermes_install.migrator import apply_install, ensure_git_repo, preview_install
from hermes_install.template_source import resolve_template_source


def main() -> int:
    try:
        source_root = resolve_template_source()
        target = ui.choose_target_directory()
        if target is None:
            ui.show_error("Hermes Install", "未选择目标目录")
            return 1

        target_repo = Path(target)
        ensure_git_repo(target_repo)

        preview = preview_install(source_root=source_root, target_repo=target_repo)
        summary = ui.build_preview_summary(preview["plan"])
        if not ui.confirm_preview(summary):
            ui.show_info("Hermes Install", "已取消安装")
            return 1

        out = apply_install(source_root=source_root, target_repo=target_repo, force=False)
        if not out.get("ok"):
            ui.show_error("Hermes Install", f"安装失败: {out}")
            return 1

        ui.show_info("Hermes Install", "安装完成")
        return 0
    except Exception as exc:
        ui.show_error("Hermes Install", f"安装失败: {exc}")
        return 1
```

```python
# append in .worktrees/hermes-learning/hermes_install/ui.py
from pathlib import Path
from tkinter import Tk, filedialog, messagebox


def choose_target_directory() -> Path | None:
    root = Tk()
    root.withdraw()
    selected = filedialog.askdirectory(title="选择要安装 Hermes 的仓库目录")
    root.destroy()
    if not selected:
        return None
    return Path(selected)


def confirm_preview(summary: str) -> bool:
    root = Tk()
    root.withdraw()
    ok = messagebox.askokcancel("Hermes 安装预览", summary)
    root.destroy()
    return bool(ok)


def show_info(title: str, message: str) -> None:
    root = Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


def show_error(title: str, message: str) -> None:
    root = Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()
```

```python
# append in .worktrees/hermes-learning/hermes_install/template_source.py
from pathlib import Path


def resolve_template_source() -> Path:
    raise NotImplementedError("template fetch not wired yet")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_main_applies_when_user_confirms .worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py::test_main_returns_nonzero_when_user_cancels -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add hermes_install/cli.py hermes_install/ui.py hermes_install/template_source.py tests/hermes_install/test_cli_flow.py
git -C .worktrees/hermes-learning commit -m "feat: wire hermes installer end-to-end gui flow"
```

---

### Task 7: Implement template source resolution for real repository tags

**Files:**
- Modify: `.worktrees/hermes-learning/hermes_install/template_source.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_template_source.py`

- [ ] **Step 1: Write the failing test**

```python
# append in .worktrees/hermes-learning/tests/hermes_install/test_template_source.py
from hermes_install import template_source


def test_latest_tag_selection_ignores_prerelease_suffixes():
    tags = ["v1.0.0-rc.1", "v1.0.0", "v0.9.9"]
    assert template_source.pick_latest_stable_tag(tags) == "v1.0.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_template_source.py::test_latest_tag_selection_ignores_prerelease_suffixes -q`
Expected: FAIL if implementation mis-parses prerelease tags

- [ ] **Step 3: Write minimal implementation**

```python
# extend .worktrees/hermes-learning/hermes_install/template_source.py
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path

TEMPLATE_REPO = "https://github.com/hansen-Mercaso/claude-closed-learning"


def list_remote_tags(repo_api_tags_url: str | None = None) -> list[str]:
    url = repo_api_tags_url or "https://api.github.com/repos/hansen-Mercaso/claude-closed-learning/tags?per_page=200"
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return [str(item.get("name", "")).strip() for item in payload if isinstance(item, dict)]


def resolve_template_source() -> Path:
    tags = list_remote_tags()
    tag = pick_latest_stable_tag(tags)

    tmp = Path(tempfile.mkdtemp(prefix="hermes-template-"))
    archive = tmp / f"{tag}.zip"
    url = f"{TEMPLATE_REPO}/archive/refs/tags/{tag}.zip"
    urllib.request.urlretrieve(url, archive)

    extract_root = tmp / "extract"
    shutil.unpack_archive(str(archive), str(extract_root))

    children = [p for p in extract_root.iterdir() if p.is_dir()]
    if len(children) != 1:
        raise ValueError("unexpected template archive structure")

    return extract_template_payload(children[0])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install/test_template_source.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add hermes_install/template_source.py tests/hermes_install/test_template_source.py
git -C .worktrees/hermes-learning commit -m "feat: resolve template source from latest stable git tag"
```

---

### Task 8: Add installer test coverage and regression run

**Files:**
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_cli_flow.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_migrator.py`
- Test: `.worktrees/hermes-learning/tests/hermes_install/test_template_source.py`

- [ ] **Step 1: Add one explicit non-git->git init regression test in migrator suite**

```python
# append in .worktrees/hermes-learning/tests/hermes_install/test_migrator.py
from pathlib import Path

from hermes_install.migrator import ensure_git_repo


def test_ensure_git_repo_is_idempotent(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    ensure_git_repo(target)
    ensure_git_repo(target)

    assert (target / ".git").exists()
```

- [ ] **Step 2: Run installer-only tests**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_install -q`
Expected: PASS

- [ ] **Step 3: Run full hermes_learning regression suite**

Run: `python -m pytest .worktrees/hermes-learning/tests/hermes_learning -q`
Expected: PASS

- [ ] **Step 4: Run end-to-end manual smoke (developer machine)**

Run: `python -m hermes_install.cli`
Expected: GUI appears, can choose directory, preview dialog appears.

- [ ] **Step 5: Commit**

```bash
git -C .worktrees/hermes-learning add tests/hermes_install/test_migrator.py tests/hermes_install/test_cli_flow.py tests/hermes_install/test_template_source.py
git -C .worktrees/hermes-learning commit -m "test: add installer regression and integration coverage"
```

---

### Task 9: Release hygiene for master + tag policy

**Files:**
- Modify: `.worktrees/hermes-learning/docs/superpowers/specs/2026-04-19-hermes-install-pipx-git-design.md` (if implementation details differ)

- [ ] **Step 1: Verify branch and tag readiness**

Run: `git -C .worktrees/hermes-learning branch --show-current && git -C .worktrees/hermes-learning tag -l`
Expected: feature branch contains completed installer changes; tags list may be empty pre-release.

- [ ] **Step 2: Merge flow prep**

Run: `git -C .worktrees/hermes-learning log --oneline --decorate -n 10`
Expected: installer tasks committed and ready for merge to master.

- [ ] **Step 3: Tag command template (post-merge on master)**

Run:
```bash
git -C .worktrees/hermes-learning checkout master
git -C .worktrees/hermes-learning pull
# after merge done:
git -C .worktrees/hermes-learning tag v0.1.0
git -C .worktrees/hermes-learning push personal master --tags
```
Expected: `v0.1.0` exists on remote master commit.

- [ ] **Step 4: Install command verification template**

Run:
```bash
pipx install "git+https://github.com/hansen-Mercaso/claude-closed-learning.git@v0.1.0"
hermes-install
```
Expected: installer launches GUI flow.

- [ ] **Step 5: Commit any final doc alignment updates**

```bash
git -C .worktrees/hermes-learning add docs/superpowers/specs/2026-04-19-hermes-install-pipx-git-design.md
git -C .worktrees/hermes-learning commit -m "docs: align hermes installer design with implementation details"
```

---

## Spec Coverage Self-Check

- pipx + git install entrypoint: Task 1
- GUI folder picker + GUI preview confirm: Task 5 + Task 6
- non-git target auto init: Task 4 + Task 8
- template from latest stable tag (`vX.Y.Z`): Task 2 + Task 7
- macOS/Windows-focused flow: Task 5 + Task 6 + Task 8
- master + tag release policy: Task 9

No spec requirement is uncovered.

## Placeholder Scan

- No TODO/TBD placeholders.
- All code steps include explicit snippets.
- All validation steps include executable commands and expected outcomes.

## Type/Signature Consistency Check

- `cli.main`, `template_source.resolve_template_source`, `migrator.ensure_git_repo`, `migrator.preview_install`, `migrator.apply_install`, and `ui.*` names are consistent across tasks.
- Tag format usage is consistently `vX.Y.Z` in selection logic and release flow.
