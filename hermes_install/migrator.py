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

    init = subprocess.run(
        ["git", "-C", str(target_repo), "init"],
        capture_output=True,
        text=True,
        check=False,
    )
    if init.returncode != 0:
        raise ValueError(f"failed to initialize git repository: {init.stderr.strip()}")


def preview_install(*, source_root: Path, target_repo: Path) -> dict:
    plan = migrate.build_migration_plan(source_root=source_root, target_repo=target_repo)
    report = migrate.render_preview(plan)
    return {"ok": True, "plan": plan, "report": report}


def apply_install(*, source_root: Path, target_repo: Path, force: bool = False) -> dict:
    plan = migrate.build_migration_plan(source_root=source_root, target_repo=target_repo)
    return migrate.apply_migration(
        plan=plan,
        source_root=source_root,
        target_repo=target_repo,
        force=force,
    )
