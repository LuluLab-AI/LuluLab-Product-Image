#!/usr/bin/env python3
"""Check the local product-image-ad runtime without using an API key."""
from __future__ import annotations
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cli = root / "scripts" / "lululab_cli.mjs"
    node = os.environ.get("LULULAB_NODE", "").strip() or shutil.which("node")
    checks: dict[str, object] = {
        "skillRoot": str(root),
        "python:PIL": importlib.util.find_spec("PIL") is not None,
        "lululabCli": str(cli) if cli.is_file() else "",
        "node": node or "",
    }
    missing: list[str] = []
    if not checks["python:PIL"]:
        missing.append("Pillow")
    if not cli.is_file():
        missing.append("scripts/lululab_cli.mjs")
    if not node:
        missing.append("Node.js 20+")
    else:
        try:
            result = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10, check=False)
            major = int(result.stdout.strip().lstrip("v").split(".")[0])
            checks["nodeVersion"] = result.stdout.strip()
            if result.returncode or major < 20:
                missing.append("Node.js 20+")
        except (OSError, ValueError, subprocess.TimeoutExpired):
            missing.append("Node.js 20+")
    if node and cli.is_file() and "Node.js 20+" not in missing:
        try:
            result = subprocess.run([node, str(cli), "--help"], capture_output=True, text=True, timeout=10, check=False)
            checks["cliHelp"] = result.returncode == 0 and "LuluLab Node.js CLI" in result.stdout
            if not checks["cliHelp"]:
                missing.append("LuluLab CLI help")
        except (OSError, subprocess.TimeoutExpired):
            missing.append("LuluLab CLI help")
    print(json.dumps({"ok": not missing, "skill": root.name, "checks": checks, "missing": missing}, ensure_ascii=False))
    return 0 if not missing else 1

if __name__ == "__main__":
    raise SystemExit(main())
