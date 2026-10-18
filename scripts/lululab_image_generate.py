#!/usr/bin/env python3
"""Generate one independent product-ad visual with the bundled LuluLab CLI."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from scripts.check_lululab_api_key import resolve_api_key, resolve_node
except ModuleNotFoundError:
    from check_lululab_api_key import resolve_api_key, resolve_node

CLI = Path(__file__).resolve().with_name('lululab_cli.mjs')
PENDING = {'created', 'pending', 'processing', 'running', 'queued', 'submitted'}
SUCCESS = {'succeeded', 'success', 'completed', 'complete'}
FAILED = {'failed', 'failure', 'error', 'cancelled', 'canceled', 'timeout', 'timedout'}

class GenerationError(RuntimeError):
    pass

KEY_MESSAGE = '当前步骤需要 LuluLab API Key。请登录 https://www.lululab.ai/，在站内 API Keys 获取，并按 Skill 的本地配置方式保存；不要在聊天中粘贴 Key。'
CREDITS_MESSAGE = 'LULULAB_CREDITS_INSUFFICIENT：积分不足，已停止新的计费提交。请登录 https://www.lululab.ai/，在站内 Recharge Credits 充值；完成后重新检查并继续当前任务。'

class CreditsInsufficient(GenerationError):
    pass

@contextmanager
def report_lock(report: Path):
    lock = report.with_suffix(report.suffix + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise GenerationError(f'任务锁已存在：{lock}；先确认原进程已结束。') from None
    try:
        os.write(fd, str(os.getpid()).encode('ascii'))
        os.close(fd)
        yield
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        lock.unlink(missing_ok=True)

def save_report(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def run_cli(node: str, key: str, args: list[str], timeout: int = 120) -> dict:
    import subprocess
    env = os.environ.copy()
    env['LULULAB_API_KEY'] = key
    try:
        result = subprocess.run([node, str(CLI), *args], env=env, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise GenerationError('LuluLab CLI 网络错误或超时；如已提交，禁止自动重提。') from None
    if result.returncode:
        try:
            error_code = json.loads(result.stderr).get('errorCode')
        except (ValueError, AttributeError):
            error_code = None
        if error_code == 'LULULAB_CREDITS_INSUFFICIENT':
            raise CreditsInsufficient(CREDITS_MESSAGE)
        if error_code in {'LULULAB_KEY_MISSING', 'LULULAB_KEY_INVALID'}:
            raise GenerationError(KEY_MESSAGE)
        if error_code == 'LULULAB_SUBMISSION_UNCERTAIN':
            raise GenerationError('LULULAB_SUBMISSION_UNCERTAIN：提交状态不确定；禁止自动重提。')
        raise GenerationError('LuluLab CLI 或网络故障；请检查连接并保留已有任务 ID。')
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise GenerationError('LuluLab CLI 返回无效 JSON；提交状态不确定时禁止重提。') from None
    if not isinstance(data, dict):
        raise GenerationError('LuluLab CLI 返回格式无效。')
    return data

def require_credits(node: str, key: str) -> None:
    data = run_cli(node, key, ['user', '--credits'])
    balance = data.get('balance')
    if type(balance) is not int:
        raise GenerationError('LuluLab 积分查询响应无效；未提交计费任务。')
    if balance <= 0:
        raise CreditsInsufficient(CREDITS_MESSAGE)

def state(value: dict) -> str:
    return str(value.get('status') or value.get('state') or '').strip().lower()

def image_url(value: dict) -> str:
    output = value.get('output', {})
    media = output.get('image') if isinstance(output, dict) else None
    url = media.get('url') if isinstance(media, dict) else media
    parsed = urlparse(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != 'https' or not parsed.netloc:
        raise GenerationError('图片任务缺少有效 HTTPS 输出地址。')
    return url

def download_image(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise GenerationError('输出图片已存在；请使用原任务记录，避免覆盖。')
    tmp = output.with_suffix(output.suffix + '.part')
    try:
        with urlopen(Request(url, headers={'User-Agent': 'product-image-ad/1'}), timeout=120) as response, tmp.open('wb') as f:
            while chunk := response.read(1024 * 1024):
                f.write(chunk)
        with Image.open(tmp) as image:
            image.verify()
        tmp.replace(output)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise GenerationError('无法下载或验证图片结果。') from None

def generate(args: argparse.Namespace) -> dict:
    report = Path(args.report).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    prompt = Path(args.prompt_file).read_text(encoding='utf-8').strip()
    if not prompt:
        raise GenerationError('图片 Prompt 不能为空。')
    refs = [Path(item).expanduser().resolve() for item in args.reference_image]
    if not refs or any(not p.is_file() or p.stat().st_size == 0 for p in refs):
        raise GenerationError('每张广告图都需要非空的产品参考图。')
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
        uploaded = []
        for path in refs:
            media = run_cli(node, key, ['upload', str(path)])
            if not isinstance(media.get('url'), str) or not isinstance(media.get('mimeType'), str):
                raise GenerationError('参考图上传响应缺少媒体地址或类型。')
            uploaded.append({'url': media['url'], 'mimeType': media['mimeType']})
        payload = {'model': 'gpt-image-2-5-sunburst', 'prompt': prompt, 'resolution': '1K',
                   'aspectRatio': args.aspect_ratio, 'referenceImages': uploaded}
        require_credits(node, key)
        save_report(report, {'status': 'submit_pending', 'taskId': '', 'output': str(output), 'workflowId': 'ImageGenV2'})
        try:
            result = run_cli(node, key, ['task', 'submit', '--workflow-id', 'ImageGenV2', '--input', json.dumps(payload, ensure_ascii=False, separators=(',', ':'))])
        except CreditsInsufficient:
            save_report(report, {'status': 'credits_required', 'taskId': '', 'output': str(output), 'workflowId': 'ImageGenV2'})
            raise
        task_id = result.get('id')
        if not isinstance(task_id, str) or not task_id.strip():
            raise GenerationError('提交响应缺少任务 ID；禁止重提。')
        save_report(report, {'status': 'submitted', 'taskId': task_id, 'output': str(output), 'workflowId': 'ImageGenV2'})
    deadline = time.monotonic() + args.poll_timeout
    while True:
        result = run_cli(node, key, ['task', 'fetch', '--id', task_id])
        current = state(result)
        if current in SUCCESS:
            url = image_url(result)
            download_image(url, output)
            finished = {'status': 'success', 'taskId': task_id, 'output': str(output), 'workflowId': 'ImageGenV2'}
            save_report(report, finished)
            return finished
        if current in FAILED:
            failed = {'status': 'terminal_failed', 'taskId': task_id, 'output': str(output), 'workflowId': 'ImageGenV2'}
            save_report(report, failed)
            return failed
        if current not in PENDING:
            raise GenerationError(f'未知任务状态：{current or "空"}；保留任务 ID，禁止重提。')
        if time.monotonic() >= deadline:
            raise GenerationError('图片任务轮询超时；保留任务 ID，只能恢复查询。')
        time.sleep(min(5, max(0, deadline - time.monotonic())))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-file', required=True)
    parser.add_argument('--reference-image', action='append', required=True)
    parser.add_argument('--aspect-ratio', default='9:16', choices=('9:16','16:9','1:1','3:4','4:3'))
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
