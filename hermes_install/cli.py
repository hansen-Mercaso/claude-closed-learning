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


if __name__ == "__main__":
    raise SystemExit(main())
