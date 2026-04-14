from __future__ import annotations

import sys
from pathlib import Path


def _parse_description(skill_file: Path) -> str:
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            desc = stripped.split(":", 1)[1].strip()
            if len(desc) >= 2 and desc[0] == desc[-1] and desc[0] in {'"', "'"}:
                return desc[1:-1]
            return desc
    return ""


def build_index(skills_root: Path, out_file: Path) -> None:
    lines: list[str] = []
    for skill_file in sorted(skills_root.glob("**/SKILL.md")):
        name = skill_file.parent.relative_to(skills_root).as_posix()
        desc = _parse_description(skill_file)
        lines.append(f"- {name}: {desc}")
    content = "\n".join(lines)
    if content:
        content += "\n"
    out_file.write_text(content, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        return 1
    build_index(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
