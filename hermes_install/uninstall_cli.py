from __future__ import annotations

from pathlib import Path

from hermes_install import ui
from hermes_install.migrator import uninstall_from_target


def main() -> int:
    try:
        target = ui.choose_target_directory()
        if target is None:
            ui.show_error("Hermes Uninstall", "未选择目标目录")
            return 1

        out = uninstall_from_target(Path(target))
        if not out.get("ok"):
            ui.show_error("Hermes Uninstall", f"卸载失败: {out}")
            return 1

        ui.show_info("Hermes Uninstall", "卸载完成")
        return 0
    except Exception as exc:
        ui.show_error("Hermes Uninstall", f"卸载失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
