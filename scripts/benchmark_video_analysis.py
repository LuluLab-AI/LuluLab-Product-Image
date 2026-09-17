#!/usr/bin/env python3
"""Delegate benchmark analysis to recreate-video-agent's safe V3 client."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    sibling = Path(__file__).resolve().parents[2] / "recreate-video-agent" / "scripts" / "server_video_analysis.py"
    override = os.environ.get("RECREATE_VIDEO_ANALYSIS_SCRIPT", "").strip()
    target = Path(override).expanduser() if override else sibling
    if not target.is_file():
        print("error: 未找到 recreate-video-agent 的 server_video_analysis.py。", file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, str(target), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
