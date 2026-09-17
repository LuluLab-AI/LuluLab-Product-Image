import importlib.util
import sys
from pathlib import Path
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from split_grid import split
from render_text_overlay import load_font, render
from test_image_blueprint import sample
from validate_image_blueprint import validate, BlueprintError


def test_grid_order_and_ratio(tmp_path):
    im = Image.new('RGB', (271, 322))
    colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan']
    for i, color in enumerate(colors):
        c, r = i % 3, i // 3
        im.paste(color, (round(c*271/3), r*161, round((c+1)*271/3), (r+1)*161))
    source = tmp_path/'grid.png'
    im.save(source)
    result = split(source, tmp_path/'cards', width=90, min_cell_width=0)
    for i, color in enumerate(colors):
        card = Image.open(tmp_path/'cards'/f'visual_{i+1:02d}.png')
        assert card.size == (90,160)
        assert card.getpixel((45,80)) == Image.new('RGB',(1,1),color).getpixel((0,0))
    assert len(result['cards']) == 6
    with pytest.raises(ValueError):
        split(source, tmp_path/'bad', bounds=[[0,0,999,999]]*6)


def test_grid9_order_and_ratio(tmp_path):
    im = Image.new('RGB', (270, 480))
    colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'orange', 'purple', 'white']
    for i, color in enumerate(colors):
        c, r = i % 3, i // 3
        im.paste(color, (c*90, r*160, (c+1)*90, (r+1)*160))
    source = tmp_path/'grid9.png'
    im.save(source)
    result = split(source, tmp_path/'cards9', width=90, min_cell_width=0)
    assert {key: result['grid'][key] for key in ('cardCount', 'columns', 'rows', 'order')} == {
        'cardCount': 9, 'columns': 3, 'rows': 3, 'order': 'row-major'
    }
    assert result['grid']['cropMode'] == 'detected-seams'
    for i, color in enumerate(colors):
        card = Image.open(tmp_path/'cards9'/f'visual_{i+1:02d}.png')
        assert card.size == (90,160)
        assert card.getpixel((45,80)) == Image.new('RGB',(1,1),color).getpixel((0,0))


def test_grid9_detects_offset_separator_bands(tmp_path):
    im = Image.new('RGB', (941, 1672), 'white')
    x_ranges = [(0, 294), (296, 609), (611, 941)]
    y_ranges = [(0, 554), (556, 1108), (1110, 1672)]
    colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'orange', 'purple', 'black']
    for color, (left, right), (top, bottom) in zip(
        colors,
        [x_range for y_range in y_ranges for x_range in x_ranges],
        [y_range for y_range in y_ranges for x_range in x_ranges],
    ):
        im.paste(color, (left, top, right, bottom))
    source = tmp_path/'offset-grid9.png'
    im.save(source)
    result = split(source, tmp_path/'offset-cards', width=90, card_count=9, min_cell_width=0)
    assert result['grid']['cropMode'] == 'detected-seams'
    assert [item['band'] for item in result['grid']['seamDetection']['vertical']] == [[294, 296], [609, 611]]
    assert [item['band'] for item in result['grid']['seamDetection']['horizontal']] == [[554, 556], [1108, 1110]]
    for i, color in enumerate(colors):
        card = Image.open(tmp_path/'offset-cards'/f'visual_{i+1:02d}.png')
        assert card.getpixel((45,80)) == Image.new('RGB',(1,1),color).getpixel((0,0))


def test_final_grid_rejects_low_source_resolution(tmp_path):
    im = Image.new('RGB', (941, 1672), 'white')
    colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'orange', 'purple', 'black']
    for i, color in enumerate(colors):
        c, r = i % 3, i // 3
        im.paste(color, (round(c*941/3), round(r*1672/3), round((c+1)*941/3), round((r+1)*1672/3)))
    source = tmp_path/'low-res-grid9.png'
    im.save(source)
    with pytest.raises(ValueError, match='网格源分辨率不足'):
        split(source, tmp_path/'low-res-cards', card_count=9)


def test_unicode_font_and_render(tmp_path):
    for text in ['It’s #02', 'Clean • playful']:
        font = load_font(text, 64)
        assert font.getbbox(text)[3] - font.getbbox(text)[1] > 25
    source = tmp_path/'source.png'
    Image.new('RGB', (720,1280), '#888888').save(source)
    render(source, tmp_path/'card.png', 'It’s #02', 'Clean • playful')
    assert Image.open(tmp_path/'card.png').size == (720,1280)


def test_v2_individual_blueprint_and_required_new_information():
    payload, blueprint = sample()
    validate(blueprint, payload)
    assert blueprint['cardPlan']['generationMode'] == 'individual'
    del blueprint['cards'][0]['newInformation']
    with pytest.raises(BlueprintError):
        validate(blueprint,payload)
