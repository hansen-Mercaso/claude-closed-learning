from __future__ import annotations

import importlib
import sys
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))


def test_uninstall_cli_module_exposes_main_callable():
    mod = importlib.import_module("hermes_install.uninstall_cli")
    assert callable(mod.main)
