from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_lingzhi_api_key.py"
SPEC = importlib.util.spec_from_file_location("check_lingzhi_api_key", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def test_missing_key_is_blocked_with_required_reminder(tmp_path, monkeypatch):
    monkeypatch.delenv("LINGZHI_API_KEY", raising=False)
    monkeypatch.delenv("LZSTUDIO_API_KEY", raising=False)
    with pytest.raises(gate.CredentialError, match="请获取灵智工坊API Key"):
        gate.resolve_api_key(config=tmp_path / "missing.json")


def test_configured_key_requires_remote_validation(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"apiKey": "secret"}), encoding="utf-8")
    completed = subprocess.CompletedProcess([], 0, '{"balance":123}', "")
    with patch.object(gate, "resolve_validation_cli", return_value=Path("/fake/lzstudio")), patch.object(
        gate.subprocess, "run", return_value=completed
    ) as run:
        gate.check(config=config)
    assert run.call_args.args[0][1:] == ["account", "--api-key", "secret", "--credits"]


def test_shared_skill_config_is_a_read_only_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("LINGZHI_API_KEY", raising=False)
    monkeypatch.delenv("LZSTUDIO_API_KEY", raising=False)
    monkeypatch.delenv("PRODUCT_IMAGE_AD_CONFIG", raising=False)
    shared = tmp_path / ".ugc-product-video" / "config.json"
    shared.parent.mkdir()
    shared.write_text(json.dumps({"apiKey": "shared-secret"}), encoding="utf-8")
    with patch.object(gate.Path, "home", return_value=tmp_path):
        assert gate.resolve_api_key() == "shared-secret"


@pytest.mark.parametrize(
    "completed",
    [
        subprocess.CompletedProcess([], 1, "", "unauthorized"),
        subprocess.CompletedProcess([], 0, '{"status":"ok"}', ""),
        subprocess.CompletedProcess([], 0, "not-json", ""),
    ],
)
def test_invalid_or_unverifiable_key_is_blocked(completed):
    with patch.object(gate.subprocess, "run", return_value=completed):
        with pytest.raises(gate.CredentialError) as raised:
            gate.validate_api_key("never-print-me", cli=Path("/fake/lzstudio"))
    assert str(raised.value) == gate.REMINDER
    assert "never-print-me" not in str(raised.value)


def test_save_happens_only_after_successful_validation(tmp_path):
    config = tmp_path / "config.json"
    with patch.object(gate.getpass, "getpass", return_value="new-secret"), patch.object(
        gate, "validate_api_key", side_effect=gate.CredentialError(gate.REMINDER)
    ):
        with pytest.raises(gate.CredentialError):
            gate.configure(config=config)
    assert not config.exists()

    with patch.object(gate.getpass, "getpass", return_value="new-secret"), patch.object(
        gate, "validate_api_key", return_value=None
    ):
        gate.configure(config=config)
    assert json.loads(config.read_text(encoding="utf-8")) == {"apiKey": "new-secret"}
    assert config.stat().st_mode & 0o777 == 0o600
