from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("logic", ROOT / "scripts" / "build_reference_ad_logic.py")
logic = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(logic)


def test_builds_non_transferable_boundary():
    result = logic.build({"爆款逻辑": {"阶段拆解": ["hook", "proof"]}, "视觉风格DNA": "warm UGC"})
    assert result["stageSequence"] == ["hook", "proof"]
    assert result["nonTransferableFacts"]
    assert "warm UGC" in result["visualPatterns"]
