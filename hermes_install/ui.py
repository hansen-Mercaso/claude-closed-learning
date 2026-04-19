from __future__ import annotations

from collections import Counter
from pathlib import Path
from tkinter import Tk, filedialog, messagebox


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
