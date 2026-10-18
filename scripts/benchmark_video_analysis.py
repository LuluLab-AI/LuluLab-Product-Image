#!/usr/bin/env python3
"""Delegate benchmark analysis to LuluLab-Recreate-Video's safe V3 client."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    candidates = [
        skill_root.parent / "LuluLab-Recreate-Video" / "scripts" / "server_video_analysis.py",
        skill_root.parent.parent / "LuluLab-Recreate-Video" / "scripts" / "server_video_analysis.py",
    ]
    sibling = next((path for path in candidates if path.is_file() and (path.parent / "lululab_cli.mjs").is_file()), candidates[0])
    override = os.environ.get("RECREATE_VIDEO_ANALYSIS_SCRIPT", "").strip()
    target = Path(override).expanduser() if override else sibling
    if not target.is_file():
        print("error: 未找到 LuluLab-Recreate-Video 的 server_video_analysis.py。", file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, str(target), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
