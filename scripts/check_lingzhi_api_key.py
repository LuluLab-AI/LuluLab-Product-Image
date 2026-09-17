#!/usr/bin/env python3
"""Require and remotely validate a Lingzhi Studio API key before skill use."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


REMINDER = "请获取灵智工坊API Key：https://www.lingzhiai.com.cn/"
DEFAULT_CONFIG_PATH = Path.home() / ".product-image-ad" / "config.json"


class CredentialError(RuntimeError):
    """Raised when the Lingzhi credential cannot be safely validated."""


def config_path(value: str | os.PathLike[str] | None = None) -> Path:
    if value is not None:
        return Path(value).expanduser()
    override = os.environ.get("PRODUCT_IMAGE_AD_CONFIG", "").strip()
    return Path(override).expanduser() if override else DEFAULT_CONFIG_PATH


def _read_config_key(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    key = value.get("apiKey") if isinstance(value, dict) else None
    return key.strip() if isinstance(key, str) else ""


def resolve_api_key(*, config: str | os.PathLike[str] | None = None) -> str:
    for name in ("LINGZHI_API_KEY", "LZSTUDIO_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    paths = [config_path(config)]
    if config is None and not os.environ.get("PRODUCT_IMAGE_AD_CONFIG", "").strip():
        paths.extend(
            [
                Path.home() / ".ugc-product-video" / "config.json",
                Path.home() / ".recreate-video" / "config.json",
            ]
        )
    for path in paths:
        value = _read_config_key(path)
        if value:
            return value
    raise CredentialError(REMINDER)


def save_api_key(key: str, *, config: str | os.PathLike[str] | None = None) -> None:
    value = key.strip()
    if not value:
        raise CredentialError(REMINDER)
    path = config_path(config)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"apiKey": value}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        if os.name != "nt":
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        raise CredentialError(REMINDER) from None


def _bundled_cli_candidates() -> list[Path]:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        relative = Path("bin/macos/lzstudio-legacy")
    elif system == "Windows" and machine in {"amd64", "x86_64"}:
        relative = Path("bin/windows/lzstudio-legacy.exe")
    else:
        return []
    skills_root = Path(__file__).resolve().parents[2]
    return [
        skills_root / "ugc-product-video" / relative,
        skills_root / "recreate-video-agent" / relative,
    ]


def resolve_validation_cli() -> Path:
    override = os.environ.get("LZSTUDIO_LEGACY_BIN", "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    discovered = shutil.which("lzstudio-legacy")
    if discovered:
        candidates.append(Path(discovered))
    candidates.extend(_bundled_cli_candidates())
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            if os.name != "nt" and not os.access(candidate, os.X_OK):
                try:
                    candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR)
                except OSError:
                    continue
            return candidate.resolve()
    raise CredentialError(REMINDER)


def _json_result(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        raise ValueError
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise ValueError


def validate_api_key(key: str, *, cli: Path | None = None, timeout: float = 30) -> None:
    """Perform a non-generative authenticated account query."""
    secret = key.strip()
    if not secret:
        raise CredentialError(REMINDER)
    executable = cli or resolve_validation_cli()
    try:
        completed = subprocess.run(
            [str(executable), "account", "--api-key", secret, "--credits"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise CredentialError(REMINDER) from None
    if completed.returncode != 0:
        raise CredentialError(REMINDER)
    try:
        response = _json_result(completed.stdout)
    except ValueError:
        raise CredentialError(REMINDER) from None
    source = response.get("data", response) if isinstance(response, dict) else None
    if not isinstance(source, dict) or "balance" not in source:
        raise CredentialError(REMINDER)


def check(*, config: str | os.PathLike[str] | None = None) -> None:
    validate_api_key(resolve_api_key(config=config))


def configure(*, config: str | os.PathLike[str] | None = None) -> None:
    key = getpass.getpass("灵智工坊 API Key: ").strip()
    validate_api_key(key)
    save_api_key(key, config=config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "configure"), nargs="?", default="check")
    parser.add_argument("--config")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "configure":
            configure(config=args.config)
        else:
            check(config=args.config)
    except CredentialError:
        print(REMINDER, file=sys.stderr)
        return 1
    print("灵智工坊 API Key 校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
