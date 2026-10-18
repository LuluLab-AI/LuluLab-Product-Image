#!/usr/bin/env python3
"""Generate and validate an imageAdBlueprint through LuluLab ChatGenV2."""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from scripts.check_lululab_api_key import resolve_api_key, resolve_node
    from scripts.local_prompt import build_prompt
    from scripts.lululab_image_generate import run_cli, require_credits, CreditsInsufficient, save_report, state, PENDING, SUCCESS, FAILED, GenerationError, report_lock
    from scripts.validate_image_blueprint import validate, BlueprintError
except ModuleNotFoundError:
    from check_lululab_api_key import resolve_api_key, resolve_node
    from local_prompt import build_prompt
    from lululab_image_generate import run_cli, require_credits, CreditsInsufficient, save_report, state, PENDING, SUCCESS, FAILED, GenerationError, report_lock
    from validate_image_blueprint import validate, BlueprintError

WORKFLOW_ID = 'ChatGenV2'

def extract_text(result: dict) -> str:
    """Accept documented and common text envelopes; never treat input prompt as output."""
    queue = [result.get('output'), result.get('result'), result.get('data'), result]
    while queue:
        value = queue.pop(0)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            if value.get('schemaVersion') == '2.0' and isinstance(value.get('cards'), list):
                return json.dumps(value, ensure_ascii=False)
            if isinstance(value.get('productName'), str) and isinstance(value.get('sellingPoints'), list):
                return json.dumps(value, ensure_ascii=False)
            for key in ('text', 'content', 'response', 'message', 'answer', 'responseText', 'generatedText'):
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    return item.strip()
                if isinstance(item, (dict, list)):
                    queue.append(item)
            for key in ('output', 'result', 'data'):
                if isinstance(value.get(key), (dict, list, str)):
                    queue.append(value[key])
        elif isinstance(value, list):
            queue.extend(value)
    raise GenerationError('ChatGenV2 成功响应缺少可识别的文本输出；保留任务 ID，勿重新提交。')

def parse_blueprint(text: str) -> dict:
    clean = text.strip()
    if clean.startswith('```'):
        lines = clean.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == '```':
            clean = '\n'.join(lines[1:-1]).strip()
    try:
        result = json.loads(clean)
    except ValueError:
        raise GenerationError('ChatGenV2 未返回合法 Blueprint JSON；保留原任务，勿自动重提。') from None
    if not isinstance(result, dict):
        raise GenerationError('ChatGenV2 Blueprint 必须是 JSON 对象。')
    return result

def generate(args: argparse.Namespace) -> dict:
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    report = Path(args.report).expanduser().resolve()
    payload = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise GenerationError('输入必须是 JSON 对象。')
    reference = json.loads(Path(args.reference_logic).read_text(encoding='utf-8')) if args.reference_logic else None
    if reference is not None and not isinstance(reference, dict):
        raise GenerationError('参考逻辑必须是 JSON 对象。')
    prompt = build_prompt(payload, reference)
    existing = json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
    if existing and existing.get('status') == 'success' and output.is_file():
        return existing
    task_id = args.resume_task_id or existing.get('taskId')
    if args.resume_task_id and existing.get('taskId') and args.resume_task_id != existing['taskId']:
        raise GenerationError('恢复任务 ID 与已保存记录不一致。')
    if existing and not task_id and existing.get('status') != 'credits_required':
        raise GenerationError('先前提交结果不确定；禁止重新提交。')
    node, key = resolve_node(), resolve_api_key()
    if not task_id:
        require_credits(node, key)
        save_report(report, {'status': 'submit_pending', 'taskId': '', 'workflowId': WORKFLOW_ID, 'output': str(output)})
        try:
            result = run_cli(node, key, ['task', 'submit', '--workflow-id', WORKFLOW_ID,
                                         '--input', json.dumps({'prompt': prompt}, ensure_ascii=False, separators=(',', ':'))])
        except CreditsInsufficient:
            save_report(report, {'status': 'credits_required', 'taskId': '', 'workflowId': WORKFLOW_ID, 'output': str(output)})
            raise
        task_id = result.get('id')
        if not isinstance(task_id, str) or not task_id.strip():
            raise GenerationError('提交响应缺少任务 ID；禁止重提。')
        save_report(report, {'status': 'submitted', 'taskId': task_id, 'workflowId': WORKFLOW_ID, 'output': str(output)})
    deadline = time.monotonic() + args.poll_timeout
    while True:
        result = run_cli(node, key, ['task', 'fetch', '--id', task_id])
        current = state(result)
        if current in SUCCESS:
            blueprint = parse_blueprint(extract_text(result))
            try:
                validate(blueprint, payload)
            except BlueprintError as exc:
                save_report(report, {'status': 'invalid_blueprint', 'taskId': task_id, 'workflowId': WORKFLOW_ID, 'message': str(exc)})
                raise GenerationError(f'生成的 Blueprint 校验未通过：{exc}；不得自动重提。') from None
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(output.suffix + '.tmp')
            temporary.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            os.replace(temporary, output)
            prompt_dir = Path(args.prompt_dir).expanduser().resolve() if args.prompt_dir else output.parent / 'prompts'
            prompt_dir.mkdir(parents=True, exist_ok=True)
            for index, card in enumerate(blueprint['cards'], 1):
                (prompt_dir / f'card_{index:02d}.txt').write_text(card['imagePrompt'] + '\n', encoding='utf-8')
            finished = {'status': 'success', 'taskId': task_id, 'workflowId': WORKFLOW_ID, 'output': str(output)}
            save_report(report, finished)
            return finished
        if current in FAILED:
            failed = {'status': 'terminal_failed', 'taskId': task_id, 'workflowId': WORKFLOW_ID}
            save_report(report, failed)
            return failed
        if current not in PENDING:
            raise GenerationError(f'未知任务状态：{current or "空"}；保留任务 ID，禁止重提。')
        if time.monotonic() >= deadline:
            raise GenerationError('ChatGenV2 轮询超时；保留任务 ID，只能恢复查询。')
        time.sleep(min(5, max(0, deadline - time.monotonic())))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--reference-logic')
    parser.add_argument('--output', required=True)
    parser.add_argument('--prompt-dir')
    parser.add_argument('--report', required=True)
    parser.add_argument('--resume-task-id')
    parser.add_argument('--poll-timeout', type=int, default=1800)
    args = parser.parse_args()
    try:
        with report_lock(Path(args.report).expanduser().resolve()):
            result = generate(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'success' else 2
    except (GenerationError, BlueprintError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'error', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
