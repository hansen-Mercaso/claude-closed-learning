# Claude Closed Learning / Hermes Install

A pipx-installable installer for Hermes Learning.

## Install

Install installer itself (SSH, track default branch):

```bash
pipx install "git+ssh://git@github.com/hansen-Mercaso/claude-closed-learning.git"
```

On Windows if `pipx` is not in PATH yet:

```powershell
py -3 -m pipx install "git+ssh://git@github.com/hansen-Mercaso/claude-closed-learning.git"
```

## Upgrade installer

```bash
pipx upgrade hermes-install
```

## Usage

Run from any directory:

```bash
hermes-install
```

What it does:

1. Resolves latest stable template tag (`vX.Y.Z`)
2. Opens a GUI folder picker (Windows/macOS)
3. Builds and shows migration preview
4. Applies installation after confirmation
5. Auto-initializes git (`git init`) when target is not a git repo

## Installed into target repository

- `scripts/hermes_learning/**`
- `.claude/settings.json` (incremental merge for learning MCP + hooks)

## Requirements

- Python 3.11+
- pipx
- git
- Network access to this repository

## Release policy

- Release branch: `master`
- Versioning: semantic tags `vX.Y.Z`
- Installer consumes latest stable tag only
