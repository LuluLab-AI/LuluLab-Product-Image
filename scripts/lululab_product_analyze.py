#!/usr/bin/env python3
"""Identify visible product facts from images through LuluLab ChatGenV2."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_lululab_api_key import resolve_api_key, resolve_node
from lululab_image_generate import run_cli, require_credits, CreditsInsufficient, save_report, state, PENDING, SUCCESS, FAILED, GenerationError, report_lock
from lululab_blueprint_generate import extract_text

WORKFLOW_ID = 'ChatGenV2'
PROMPT = '''请仅分析本次请求附带的商品图片，生成且只生成一个 JSON 对象，不要 Markdown 或解释。不要把本提示词或文件名当作商品事实。
字段固定为 productName、productType、sellingPoints、targetAudience、visibleFeatures、unknowns。所有字段必须存在：前四个及 unknowns 中每项为中文字符串，sellingPoints 和 visibleFeatures 为字符串数组，unknowns 为字符串数组。
productName 只写图中可靠可见的品牌/品名；无法辨认则为空。productType 只写可靠可见的商品类别；不能确定则为空。sellingPoints 最多 3 项，只能表述图片确实可见的设计、形态或使用方式，不得虚构功效、成分、参数、认证、销量、口碑、价格或优惠。targetAudience 只有图片能可靠支持时才填写，否则为空。visibleFeatures 列出可见颜色、包装、Logo、结构和关键部件；不清楚的地方列入 unknowns，不猜测背面或内部。多图之间出现冲突时放入 unknowns，不强行合并。'''

def normalize_analysis(value: dict, images: list[Path]) -> dict:
    required_text = ('productName', 'productType', 'targetAudience')
    required_lists = ('sellingPoints', 'visibleFeatures', 'unknowns')
    for field in required_text:
        if not isinstance(value.get(field), str):
            raise GenerationError(f'商品识别结果缺少字符串字段：{field}。')
    for field in required_lists:
        if not isinstance(value.get(field), list) or not all(isinstance(item, str) for item in value[field]):
            raise GenerationError(f'商品识别结果缺少字符串数组：{field}。')
    if len(value['sellingPoints']) > 3:
        raise GenerationError('商品识别结果包含超过 3 个卖点。')
    return {
        'source': 'LuluLab ChatGenV2',
        'productName': value['productName'].strip(),
        'productType': value['productType'].strip(),
        'sellingPoints': [item.strip() for item in value['sellingPoints'] if item.strip()],
        'targetAudience': value['targetAudience'].strip(),
        'visibleFeatures': [item.strip() for item in value['visibleFeatures'] if item.strip()],
        'unknowns': [item.strip() for item in value['unknowns'] if item.strip()],
        'productImages': [{'path': str(path)} for path in images],
    }

def parse_analysis_json(text: str) -> dict:
    clean = text.strip()
    if clean.startswith('```'):
        lines = clean.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == '```':
            clean = '\n'.join(lines[1:-1]).strip()
    try:
        value = json.loads(clean)
    except ValueError:
        raise GenerationError('ChatGenV2 未返回合法商品识别 JSON；保留任务 ID，不自动重提。') from None
    if not isinstance(value, dict):
        raise GenerationError('商品识别结果必须是 JSON 对象。')
    return value

def generate(args: argparse.Namespace) -> dict:
    images = [Path(item).expanduser().resolve() for item in args.image]
    if not images or any(not path.is_file() or path.stat().st_size == 0 for path in images):
        raise GenerationError('至少需要一张非空商品图。')
    digest = hashlib.sha256()
    for path in images:
        digest.update(str(path).encode('utf-8'))
        with path.open('rb') as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    fingerprint = digest.hexdigest()
    output = Path(args.output).expanduser().resolve()
    report = Path(args.report).expanduser().resolve()
    existing = json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
    if existing and existing.get('inputFingerprint') != fingerprint:
        raise GenerationError('商品图与已有任务记录不一致；不能复用该任务。')
    if output.exists() and not existing:
        raise GenerationError('识别输出已存在但缺少任务记录；请使用新的输出路径。')
    if existing and existing.get('status') == 'success' and output.is_file():
        return existing
    task_id = args.resume_task_id or existing.get('taskId')
    if args.resume_task_id and existing.get('taskId') and args.resume_task_id != existing['taskId']:
        raise GenerationError('恢复任务 ID 与已保存记录不一致。')
    if existing and not task_id and existing.get('status') != 'credits_required':
        raise GenerationError('先前提交结果不确定；禁止重新提交。')
    node, key = resolve_node(), resolve_api_key()
    if not task_id:
        uploaded = []
        for path in images:
            media = run_cli(node, key, ['upload', str(path)])
            if not isinstance(media.get('url'), str) or not isinstance(media.get('mimeType'), str):
                raise GenerationError('商品图上传响应缺少媒体地址或类型。')
            uploaded.append({'url': media['url'], 'mimeType': media['mimeType']})
        payload = {'prompt': PROMPT, 'images': uploaded}
        require_credits(node, key)
        save_report(report, {'status': 'submit_pending', 'taskId': '', 'workflowId': WORKFLOW_ID, 'output': str(output), 'inputFingerprint': fingerprint})
        try:
            result = run_cli(node, key, ['task', 'submit', '--workflow-id', WORKFLOW_ID,
                                         '--input', json.dumps(payload, ensure_ascii=False, separators=(',', ':'))])
        except CreditsInsufficient:
            save_report(report, {'status': 'credits_required', 'taskId': '', 'workflowId': WORKFLOW_ID, 'output': str(output), 'inputFingerprint': fingerprint})
            raise
        task_id = result.get('id')
        if not isinstance(task_id, str) or not task_id.strip():
            raise GenerationError('提交响应缺少任务 ID；禁止重提。')
        save_report(report, {'status': 'submitted', 'taskId': task_id, 'workflowId': WORKFLOW_ID, 'output': str(output), 'inputFingerprint': fingerprint})
    deadline = time.monotonic() + args.poll_timeout
    while True:
        result = run_cli(node, key, ['task', 'fetch', '--id', task_id])
        current = state(result)
        if current in SUCCESS:
            data = parse_analysis_json(extract_text(result))
            analysis = normalize_analysis(data, images)
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(output.suffix + '.tmp')
            temporary.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            os.replace(temporary, output)
            finished = {'status': 'success', 'taskId': task_id, 'workflowId': WORKFLOW_ID, 'output': str(output), 'inputFingerprint': fingerprint}
            save_report(report, finished)
            return finished
        if current in FAILED:
            failed = {'status': 'terminal_failed', 'taskId': task_id, 'workflowId': WORKFLOW_ID, 'inputFingerprint': fingerprint}
            save_report(report, failed)
            return failed
        if current not in PENDING:
            raise GenerationError(f'未知任务状态：{current or "空"}；保留任务 ID，禁止重提。')
        if time.monotonic() >= deadline:
            raise GenerationError('商品图识别任务轮询超时；保留任务 ID，只能恢复查询。')
        time.sleep(min(5, max(0, deadline - time.monotonic())))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', action='append', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--resume-task-id')
    parser.add_argument('--poll-timeout', type=int, default=1800)
    args = parser.parse_args()
    try:
        with report_lock(Path(args.report).expanduser().resolve()):
            result = generate(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'success' else 2
    except (GenerationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
