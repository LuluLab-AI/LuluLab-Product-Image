#!/usr/bin/env python3
"""Verify a LuluLab API key with the bundled Node.js CLI without generating media."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


REMINDER = "当前商品图处理需要 LuluLab API Key。请登录 https://www.lululab.ai/，在站内 API Keys 获取，并在本机安全配置；不要在聊天中粘贴 Key。"
DEFAULT_CONFIG_PATH = Path.home() / ".product-image-ad-lululab" / "config.json"
CLI = Path(__file__).resolve().with_name("lululab_cli.mjs")


class CredentialError(RuntimeError):
    pass


def config_path(value: str | None = None) -> Path:
    return Path(value or os.environ.get("PRODUCT_IMAGE_AD_CONFIG") or DEFAULT_CONFIG_PATH).expanduser()


def read_config_key(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    key = data.get("apiKey") if isinstance(data, dict) else None
    return key.strip() if isinstance(key, str) else ""


def resolve_api_key(config: str | None = None) -> str:
    for name in ("LULULAB_API_KEY", "LINGZHI_API_KEY", "LZSTUDIO_API_KEY"):
        key = os.environ.get(name, "").strip()
        if key:
            return key
    paths = [config_path(config)]
    if config is None and not os.environ.get("PRODUCT_IMAGE_AD_CONFIG"):
        paths.append(Path.home() / ".recreate-video-lululab" / "config.json")
    for path in paths:
        key = read_config_key(path)
        if key:
            return key
    raise CredentialError(REMINDER)


def resolve_node() -> str:
    node = os.environ.get("LULULAB_NODE", "").strip() or shutil.which("node")
    if not node or not CLI.is_file():
        raise CredentialError("需要 Node.js 20+ 和随包的 scripts/lululab_cli.mjs。")
    try:
        version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10, check=False)
        major = int(version.stdout.strip().lstrip("v").split(".")[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise CredentialError("无法验证 Node.js 版本。") from None
    if version.returncode or major < 20:
        raise CredentialError("需要 Node.js 20+。")
    return node


def validate_api_key(key: str, *, node: str | None = None, timeout: float = 30) -> None:
    if not key.strip():
        raise CredentialError(REMINDER)
    executable = node or resolve_node()
    env = os.environ.copy()
    env["LULULAB_API_KEY"] = key.strip()
    try:
        result = subprocess.run(
            [executable, str(CLI), "user", "--credits"],
            env=env, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise CredentialError("LuluLab 鉴权请求失败或超时。") from None
    if result.returncode:
        try:
            code = json.loads(result.stderr).get('errorCode')
        except (ValueError, AttributeError):
            code = None
        if code in {'LULULAB_KEY_MISSING', 'LULULAB_KEY_INVALID'}:
            raise CredentialError(REMINDER)
        if code == 'LULULAB_CREDITS_INSUFFICIENT':
            return  # The Key authenticated; the billable-submit gate handles credits later.
        raise CredentialError('LuluLab 账户校验遇到网络或 CLI 故障；请检查连接后重试。')
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise CredentialError("LuluLab 返回无法验证的账户响应。") from None
    if not isinstance(data, dict) or type(data.get("balance")) is not int:
        raise CredentialError("LuluLab 返回无法验证的账户响应。")


def save_api_key(key: str, config: str | None = None) -> None:
    path = config_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.parent.chmod(0o700)
    path.write_text(json.dumps({"apiKey": key.strip()}, ensure_ascii=False), encoding="utf-8")
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("check", "configure"), default="check")
    parser.add_argument("--config")
    args = parser.parse_args()
    try:
        key = getpass.getpass("LuluLab API Key: ") if args.command == "configure" else resolve_api_key(args.config)
        validate_api_key(key)
        if args.command == "configure":
            save_api_key(key, args.config)
    except (CredentialError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("LuluLab API Key 校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
