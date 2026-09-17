from pathlib import Path
import importlib.util

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("overlay", ROOT / "scripts" / "render_text_overlay.py")
overlay = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(overlay)


def test_overlay_smoke(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "card.png"
    Image.new("RGB", (360, 640), "#6688aa").save(source)
    overlay.render(source, output, "A simple headline", "Readable subhead", "NEW", "top-title")
    assert output.is_file()
    assert Image.open(output).size == (360, 640)
