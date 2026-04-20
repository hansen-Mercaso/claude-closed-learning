from __future__ import annotations

import copy
import json
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path


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


def _collect_source_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(source_root)
        if "__pycache__" in rel.parts or rel.suffix.lower() == ".pyc":
            continue
        files.append(rel)
    files.sort(key=lambda p: p.as_posix())
    return files


def _ensure_hook_block(settings: dict, event: str) -> list[dict]:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        settings["hooks"] = {}
        hooks = settings["hooks"]

    blocks = hooks.setdefault(event, [])
    if not isinstance(blocks, list):
        hooks[event] = []
        blocks = hooks[event]
    return blocks


def _inject_command_hook(blocks: list[dict], command: str, matcher: str | None = None) -> None:
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_matcher = block.get("matcher")
        if matcher is not None:
            if block_matcher != matcher:
                continue
        elif block_matcher is not None:
            continue

        hooks = block.get("hooks")
        if not isinstance(hooks, list):
            continue

        for hook in hooks:
            if isinstance(hook, dict) and hook.get("type") == "command" and hook.get("command") == command:
                return

    entry: dict[str, object] = {"hooks": [{"type": "command", "command": command}]}
    if matcher is not None:
        entry["matcher"] = matcher
    blocks.append(entry)


def _merge_learning_settings(existing: dict) -> dict:
    out = copy.deepcopy(existing) if isinstance(existing, dict) else {}

    mcp_servers = out.setdefault("mcpServers", {})
    if not isinstance(mcp_servers, dict):
        out["mcpServers"] = {}
        mcp_servers = out["mcpServers"]

    mcp_servers["learning"] = {
        "command": "python",
        "args": ["scripts/hermes_learning/mcp/server.py"],
    }

    stop_blocks = _ensure_hook_block(out, "Stop")
    _inject_command_hook(stop_blocks, "scripts/hermes_learning/hooks/stop-hook.sh")

    precompact_blocks = _ensure_hook_block(out, "PreCompact")
    _inject_command_hook(
        precompact_blocks,
        "FORCE_EXTRACTION=true scripts/hermes_learning/hooks/stop-hook.sh",
        matcher="manual|auto",
    )

    session_start_blocks = _ensure_hook_block(out, "SessionStart")
    _inject_command_hook(session_start_blocks, "scripts/hermes_learning/hooks/session-start.sh")

    return out


def _build_migration_plan(*, source_root: Path, target_repo: Path) -> dict:
    rel_files = _collect_source_files(source_root)
    file_changes: list[dict] = []

    for rel in rel_files:
        src = source_root / rel
        dst = target_repo / "scripts" / "hermes_learning" / rel

        if not dst.exists():
            file_changes.append({"type": "add", "path": dst.as_posix(), "rel": rel.as_posix()})
            continue

        if not dst.is_file():
            file_changes.append({"type": "conflict", "path": dst.as_posix(), "rel": rel.as_posix()})
            continue

        if src.read_bytes() == dst.read_bytes():
            file_changes.append({"type": "skip", "path": dst.as_posix(), "rel": rel.as_posix()})
            continue

        file_changes.append({"type": "conflict", "path": dst.as_posix(), "rel": rel.as_posix()})

    settings_path = target_repo / ".claude" / "settings.json"
    existing: dict = {}
    if settings_path.exists():
        loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        existing = loaded if isinstance(loaded, dict) else {}

    merged = _merge_learning_settings(existing)

    return {
        "file_changes": file_changes,
        "settings_change": {
            "existing": existing,
            "merged": merged,
            "changed": existing != merged,
            "path": settings_path.as_posix(),
        },
    }


def _render_preview(plan: dict) -> str:
    lines = ["# Migration Preview", "## File Changes"]
    for item in plan.get("file_changes", []):
        lines.append(f"- {item['type']}: {item['rel']}")

    settings_change = plan.get("settings_change", {})
    lines.append("## Settings")
    lines.append(f"- path: {settings_change.get('path', '')}")
    lines.append(f"- changed: {bool(settings_change.get('changed'))}")
    return "\n".join(lines) + "\n"


def _backup_dir(target_repo: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return target_repo / ".claude" / "migrate-backup" / stamp


def _atomic_copy_file_with_mode(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.tmp")
    shutil.copyfile(src, tmp)
    if shutil.os.name != "nt":
        os_mode = src.stat().st_mode
        tmp.chmod(stat.S_IMODE(os_mode))
    tmp.replace(dst)


def _apply_migration(*, plan: dict, source_root: Path, target_repo: Path, force: bool) -> dict:
    conflicts = [item for item in plan.get("file_changes", []) if item.get("type") == "conflict"]
    if conflicts and not force:
        return {"ok": False, "error_code": "conflict_detected", "conflicts": conflicts}

    has_file_changes = any(item.get("type") != "skip" for item in plan.get("file_changes", []))
    settings_change = plan.get("settings_change", {})
    has_settings_change = bool(settings_change.get("changed"))

    backup_root: Path | None = None
    if has_file_changes or has_settings_change:
        backup_root = _backup_dir(target_repo)
        backup_root.mkdir(parents=True, exist_ok=True)

    for item in plan.get("file_changes", []):
        if item.get("type") == "skip":
            continue

        rel = Path(item["rel"])
        src = source_root / rel
        dst = target_repo / "scripts" / "hermes_learning" / rel

        if backup_root is not None and dst.exists():
            backup_path = backup_root / "scripts" / "hermes_learning" / rel
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup_path)

        _atomic_copy_file_with_mode(src, dst)

    settings_path = target_repo / ".claude" / "settings.json"
    if has_settings_change:
        if backup_root is not None and settings_path.exists():
            backup_settings = backup_root / ".claude" / "settings.json"
            backup_settings.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(settings_path, backup_settings)

        merged = settings_change.get("merged", {})
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"ok": True, "backup_dir": (backup_root.as_posix() if backup_root is not None else "")}


def preview_install(*, source_root: Path, target_repo: Path) -> dict:
    plan = _build_migration_plan(source_root=source_root, target_repo=target_repo)
    report = _render_preview(plan)
    return {"ok": True, "plan": plan, "report": report}


def apply_install(*, source_root: Path, target_repo: Path, force: bool = False) -> dict:
    plan = _build_migration_plan(source_root=source_root, target_repo=target_repo)
    return _apply_migration(
        plan=plan,
        source_root=source_root,
        target_repo=target_repo,
        force=force,
    )


_LEARNING_HOOK_COMMANDS = {
    "scripts/hermes_learning/hooks/stop-hook.sh",
    "FORCE_EXTRACTION=true scripts/hermes_learning/hooks/stop-hook.sh",
    "scripts/hermes_learning/hooks/session-start.sh",
}


def _remove_learning_command_hooks(settings: dict) -> None:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return

    for event, blocks in list(hooks.items()):
        if not isinstance(blocks, list):
            continue

        kept_blocks: list[object] = []
        for block in blocks:
            if not isinstance(block, dict):
                kept_blocks.append(block)
                continue

            block_hooks = block.get("hooks")
            if not isinstance(block_hooks, list):
                kept_blocks.append(block)
                continue

            kept_hooks: list[object] = []
            for hook in block_hooks:
                if (
                    isinstance(hook, dict)
                    and hook.get("type") == "command"
                    and hook.get("command") in _LEARNING_HOOK_COMMANDS
                ):
                    continue
                kept_hooks.append(hook)

            if kept_hooks:
                updated_block = dict(block)
                updated_block["hooks"] = kept_hooks
                kept_blocks.append(updated_block)

        hooks[event] = kept_blocks


def _is_path_within(base_path: Path, candidate_path: Path) -> bool:
    try:
        candidate_path.relative_to(base_path)
    except ValueError:
        return False
    return True


def uninstall_from_target(target_repo: Path) -> dict:
    if not target_repo.exists() or not target_repo.is_dir():
        return {
            "ok": False,
            "error_code": "target_missing",
            "message": f"target repo does not exist: {target_repo}",
        }

    target_root = target_repo.resolve()
    settings_path = target_repo / ".claude" / "settings.json"
    resolved_settings_path: Path | None = None
    settings: dict | None = None
    if settings_path.exists():
        if settings_path.is_symlink():
            return {
                "ok": False,
                "error_code": "unsafe_settings_path",
                "message": "settings.json must not be a symlink",
                "path": settings_path.as_posix(),
            }

        resolved_settings_path = settings_path.resolve()
        if not _is_path_within(target_root, resolved_settings_path):
            return {
                "ok": False,
                "error_code": "unsafe_settings_path",
                "message": "resolved settings.json path must stay within target repo",
                "path": settings_path.as_posix(),
                "resolved_path": resolved_settings_path.as_posix(),
            }

        try:
            loaded = json.loads(resolved_settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "error_code": "invalid_settings_json",
                "message": str(exc),
                "path": settings_path.as_posix(),
            }

        if not isinstance(loaded, dict):
            return {
                "ok": False,
                "error_code": "invalid_settings_json",
                "message": "settings.json must contain a JSON object",
                "path": settings_path.as_posix(),
            }
        settings = loaded

    learning_path = target_repo / "scripts" / "hermes_learning"
    try:
        if learning_path.is_symlink():
            learning_path.unlink()
        elif learning_path.exists():
            if learning_path.is_dir():
                shutil.rmtree(learning_path)
            else:
                learning_path.unlink()
    except OSError as exc:
        return {
            "ok": False,
            "error_code": "learning_path_delete_failed",
            "path": learning_path.as_posix(),
            "message": str(exc),
        }

    if settings is not None and resolved_settings_path is not None:
        mcp_servers = settings.get("mcpServers")
        if isinstance(mcp_servers, dict):
            mcp_servers.pop("learning", None)

        _remove_learning_command_hooks(settings)
        try:
            resolved_settings_path.write_text(
                json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            return {
                "ok": False,
                "error_code": "settings_write_failed",
                "path": settings_path.as_posix(),
                "message": str(exc),
            }

    return {"ok": True}
