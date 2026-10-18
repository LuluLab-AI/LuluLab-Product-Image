from __future__ import annotations
import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('check_lululab_api_key', ROOT / 'scripts/check_lululab_api_key.py')
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

def test_missing_key_is_blocked(tmp_path, monkeypatch):
    for name in ('LULULAB_API_KEY', 'LINGZHI_API_KEY', 'LZSTUDIO_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(gate.CredentialError):
        gate.resolve_api_key(str(tmp_path / 'missing.json'))

def test_key_is_passed_only_in_environment(tmp_path):
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'apiKey': 'secret'}), encoding='utf-8')
    result = subprocess.CompletedProcess([], 0, '{"balance":123}', '')
    with patch.object(gate, 'resolve_node', return_value='/fake/node'), patch.object(gate.subprocess, 'run', return_value=result) as run:
        gate.validate_api_key(gate.resolve_api_key(str(config)))
    args = run.call_args.args[0]
    assert args[-2:] == ['user', '--credits']
    assert 'secret' not in args
    assert run.call_args.kwargs['env']['LULULAB_API_KEY'] == 'secret'

def test_recreate_video_config_is_read_only_fallback(tmp_path, monkeypatch):
    for name in ('LULULAB_API_KEY', 'LINGZHI_API_KEY', 'LZSTUDIO_API_KEY', 'PRODUCT_IMAGE_AD_CONFIG'):
        monkeypatch.delenv(name, raising=False)
    shared = tmp_path / '.recreate-video-lululab/config.json'
    shared.parent.mkdir()
    shared.write_text(json.dumps({'apiKey': 'shared-secret'}), encoding='utf-8')
    with patch.object(gate.Path, 'home', return_value=tmp_path):
        assert gate.resolve_api_key() == 'shared-secret'

@pytest.mark.parametrize('result', [
    subprocess.CompletedProcess([], 1, '', 'unauthorized'),
    subprocess.CompletedProcess([], 0, '{"status":"ok"}', ''),
    subprocess.CompletedProcess([], 0, 'not-json', ''),
])
def test_invalid_or_unverifiable_key_is_blocked(result):
    with patch.object(gate.subprocess, 'run', return_value=result):
        with pytest.raises(gate.CredentialError) as error:
            gate.validate_api_key('never-print-me', node='/fake/node')
    assert 'never-print-me' not in str(error.value)

def test_config_is_private(tmp_path):
    config = tmp_path / 'config.json'
    gate.save_api_key('new-secret', str(config))
    assert json.loads(config.read_text(encoding='utf-8')) == {'apiKey': 'new-secret'}
    assert config.stat().st_mode & 0o777 == 0o600
