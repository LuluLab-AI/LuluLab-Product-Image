from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

image = load('lululab_image_generate')
blueprint = load('lululab_blueprint_generate')
product = load('lululab_product_analyze')

def test_new_submission_requires_positive_read_only_credits():
    with patch.object(image, 'run_cli', return_value={'balance': 0}) as cli:
        with pytest.raises(image.CreditsInsufficient, match='LULULAB_CREDITS_INSUFFICIENT'):
            image.require_credits('node', 'private-key')
    assert cli.call_args.args[2] == ['user', '--credits']
    with patch.object(image, 'run_cli', side_effect=image.GenerationError('network failure')):
        with pytest.raises(image.GenerationError, match='network failure'):
            image.require_credits('node', 'private-key')

def test_product_images_are_uploaded_for_chatgen_recognition(tmp_path):
    first = tmp_path / 'front.jpg'
    second = tmp_path / 'back.png'
    first.write_bytes(b'front')
    second.write_bytes(b'back')
    args = argparse.Namespace(image=[str(first), str(second)], output=str(tmp_path/'product_analysis.json'),
                              report=str(tmp_path/'product.task.json'), resume_task_id=None, poll_timeout=1)
    analysis = {'productName':'', 'productType':'瓶装商品', 'sellingPoints':['蓝色包装'],
                'targetAudience':'', 'visibleFeatures':['蓝色瓶身'], 'unknowns':['背面文字不可辨认']}
    replies = [
        {'url':'https://example.com/front', 'mimeType':'image/jpeg'},
        {'url':'https://example.com/back', 'mimeType':'image/png'},
        {'id':'recognition-task-1'},
        {'status':'Succeeded', 'output':{'text':json.dumps(analysis, ensure_ascii=False)}},
    ]
    with patch.object(product, 'resolve_node', return_value='node'), patch.object(product, 'resolve_api_key', return_value='secret'), \
         patch.object(product, 'run_cli', side_effect=replies) as cli, patch.object(product, 'require_credits'):
        result = product.generate(args)
    submit = cli.call_args_list[2].args[2]
    assert submit[:4] == ['task', 'submit', '--workflow-id', 'ChatGenV2']
    payload = json.loads(submit[-1])
    assert [m['mimeType'] for m in payload['images']] == ['image/jpeg', 'image/png']
    assert [m['url'] for m in payload['images']] == ['https://example.com/front', 'https://example.com/back']
    assert 'front.jpg' not in payload['prompt']
    assert result['taskId'] == 'recognition-task-1'
    saved = json.loads(Path(args.output).read_text())
    assert saved['source'] == 'LuluLab ChatGenV2'
    assert saved['sellingPoints'] == ['蓝色包装']
    assert len(saved['productImages']) == 2

def test_product_analysis_does_not_reuse_task_for_changed_image(tmp_path):
    photo = tmp_path / 'product.png'
    photo.write_bytes(b'original')
    args = argparse.Namespace(image=[str(photo)], output=str(tmp_path/'analysis.json'),
                              report=str(tmp_path/'task.json'), resume_task_id=None, poll_timeout=1)
    analysis = {'productName':'', 'productType':'盒子', 'sellingPoints':[],
                'targetAudience':'', 'visibleFeatures':['方形'], 'unknowns':[]}
    replies = [
        {'url':'https://example.com/product', 'mimeType':'image/png'}, {'id':'task-one'},
        {'status':'Succeeded', 'output':{'text':json.dumps(analysis, ensure_ascii=False)}},
    ]
    with patch.object(product, 'resolve_node', return_value='node'), patch.object(product, 'resolve_api_key', return_value='secret'), \
         patch.object(product, 'run_cli', side_effect=replies), patch.object(product, 'require_credits'):
        product.generate(args)
    photo.write_bytes(b'changed')
    with patch.object(product, 'run_cli') as cli:
        with pytest.raises(product.GenerationError, match='不一致'):
            product.generate(args)
    cli.assert_not_called()

def test_image_uses_lululab_workflow_and_preserves_id(tmp_path):
    product = tmp_path / 'product.png'
    product.write_bytes(b'picture')
    prompt = tmp_path / 'prompt.txt'
    prompt.write_text('product photo', encoding='utf-8')
    args = argparse.Namespace(prompt_file=str(prompt), reference_image=[str(product)], aspect_ratio='9:16',
                              output=str(tmp_path/'visual.png'), report=str(tmp_path/'task.json'),
                              resume_task_id=None, poll_timeout=1)
    replies = [
        {'url': 'https://example.com/product', 'mimeType': 'image/png'},
        {'id': 'image-task-1'},
        {'status': 'Succeeded', 'output': {'image': {'url': 'https://example.com/result'}}},
    ]
    with patch.object(image, 'resolve_node', return_value='node'), patch.object(image, 'resolve_api_key', return_value='secret'), \
         patch.object(image, 'run_cli', side_effect=replies) as cli, patch.object(image, 'require_credits'), patch.object(image, 'download_image'):
        result = image.generate(args)
    assert result['taskId'] == 'image-task-1'
    submit = cli.call_args_list[1].args[2]
    assert submit[:4] == ['task', 'submit', '--workflow-id', 'ImageGenV2']
    payload = json.loads(submit[-1])
    assert payload['model'] == 'gpt-image-2-5-sunburst'
    assert payload['referenceImages'][0]['url'] == 'https://example.com/product'
    assert 'secret' not in str(submit)
    assert json.loads(Path(args.report).read_text())['taskId'] == 'image-task-1'

def test_image_unknown_submission_is_not_retried(tmp_path):
    report = tmp_path / 'task.json'
    report.write_text(json.dumps({'status':'submit_pending','taskId':''}))
    product = tmp_path / 'product.png'
    product.write_bytes(b'picture')
    prompt = tmp_path / 'prompt.txt'
    prompt.write_text('photo')
    args = argparse.Namespace(prompt_file=str(prompt), reference_image=[str(product)], aspect_ratio='9:16',
                              output=str(tmp_path/'visual.png'), report=str(report), resume_task_id=None, poll_timeout=1)
    with patch.object(image, 'run_cli') as cli:
        with pytest.raises(image.GenerationError, match='禁止重新提交'):
            image.generate(args)
    cli.assert_not_called()

def test_chatgen_blueprint_exports_exact_card_prompts(tmp_path):
    source = tmp_path/'input.json'
    source.write_text(json.dumps({'productBrief': {'productImages':[{'path':'product.png'}]}, 'userConfig': {'cardsPerSet':1}}))
    output = tmp_path/'blueprint.json'
    args = argparse.Namespace(input=str(source), reference_logic=None, output=str(output), report=str(tmp_path/'task.json'),
                              prompt_dir=None, resume_task_id=None, poll_timeout=1)
    generated = {'schemaVersion':'2.0', 'cards':[{'imagePrompt':'exact prompt from LuluLab'}]}
    replies = [{'id':'chat-task-1'}, {'status':'Succeeded', 'output':{'text':json.dumps(generated)}}]
    with patch.object(blueprint, 'resolve_node', return_value='node'), patch.object(blueprint, 'resolve_api_key', return_value='secret'), \
         patch.object(blueprint, 'run_cli', side_effect=replies) as cli, patch.object(blueprint, 'require_credits'), patch.object(blueprint, 'validate'):
        result = blueprint.generate(args)
    assert result['taskId'] == 'chat-task-1'
    submit = cli.call_args_list[0].args[2]
    assert submit[:4] == ['task', 'submit', '--workflow-id', 'ChatGenV2']
    assert list(json.loads(submit[-1])) == ['prompt']
    assert (tmp_path/'prompts/card_01.txt').read_text() == 'exact prompt from LuluLab\n'
    assert json.loads(output.read_text()) == generated
