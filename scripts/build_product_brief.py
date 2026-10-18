#!/usr/bin/env python3
"""Delegate conservative product-card construction to LuluLab-Recreate-Video."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    sibling = Path(__file__).resolve().parents[2] / "LuluLab-Recreate-Video" / "scripts" / "build_product_brief.py"
    override = os.environ.get("PRODUCT_BRIEF_SCRIPT", "").strip()
    target = Path(override).expanduser() if override else sibling
    if not target.is_file():
        print("error: 未找到 LuluLab-Recreate-Video 的 build_product_brief.py。", file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, str(target), *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
