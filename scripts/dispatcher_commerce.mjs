#!/usr/bin/env node
/** Customer/Dispatcher commerce adapter. Node >=20, no dependencies. */
import { readFile, writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { resolve, dirname, basename } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { LuluLabClient, resolveApiKey, imageMimeType } from './lululab_cli.mjs';
const SCHEMA = 'lululab.dispatcher.commerce.v1';
const terminal = task => ['Succeeded', 'Failed', 'Cancelled'].includes(task?.status);
const guid = value => typeof value === 'string' && /^[a-f\d]{8}(?:-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(value);
function url(value) {
  const parsed = new URL(value);
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password) throw Error('Media must use HTTPS without credentials.');
  return parsed.href;
}
function refs(files = []) {
  if (!Array.isArray(files)) throw Error('References must be arrays.');
  return files.map(file => {
    if (!file?.mimeType?.startsWith('image/')) throw Error('Expected uploaded image references.');
    const expiredAt = file.expiredAt || file.expiresAt;
    if (expiredAt && (!Number.isFinite(Date.parse(expiredAt)) || Date.parse(expiredAt) <= Date.now())) throw Error('Reference image expired.');
    return { url: url(file.url || file.location), mimeType: file.mimeType, ...(expiredAt ? { expiredAt } : {}) };
  });
}
function integer(value, min, max, label) {
  if (!Number.isInteger(value) || value < min || value > max) throw Error(`Invalid ${label}: ${min}–${max}.`);
  return value;
}
export function buildPlan(config) {
  if (config?.kind !== 'image') throw Error('This skill requires kind=image.');
  const c = { aspectRatio: '9:16', targetCountry: 'United States', targetLanguage: 'en-US', creativeRequirement: '', ...config };
  if (!['video', 'image'].includes(c.kind)) throw Error('kind must be video or image.');
  c.productImages = refs(c.productImages); c.creatorImages = refs(c.creatorImages);
  if (!c.productImages.length) throw Error('Product images are required.');
  if (c.creatorImages.length > 1 && c.kind === 'image') throw Error('Frontend image mode supports one creator image.');
  if (typeof c.creativeRequirement !== 'string') throw Error('creativeRequirement must be text.');
  if (c.kind === 'video') {
    c.model ??= 'seedance-2-fast'; c.duration ??= 15; c.count ??= 1; c.resolution ??= '720p'; c.generateAudio ??= true; c.creativeType ??= 'auto';
    integer(c.duration, 4, 60, 'duration'); integer(c.count, 1, 20, 'video count');
    if (!['auto', 'productPitch', 'storyDrivenAd', 'lifestyleSeeding'].includes(c.creativeType)) throw Error('Invalid creativeType.');
    if (!['seedance-2-mini', 'seedance-2-fast', 'seedance-2', 'seedance-2-5', 'wan-3', 'minimax-h3', 'google-omni', 'grok-imagine-1-5-preview'].includes(c.model)) throw Error('Unsupported commerce model.');
    if (typeof c.generateAudio !== 'boolean') throw Error('generateAudio must be boolean.');
    const standard = ['21:9', '16:9', '4:3', '1:1', '3:4', '9:16'];
    const ratios = c.model === 'google-omni' ? ['9:16', '16:9'] : c.model === 'wan-3' ? ['9:16', '16:9', '1:1', '3:4', '4:3'] : c.model.startsWith('grok-') ? ['16:9', '4:3', '3:2', '9:16', '3:4', '1:1', '2:3'] : standard;
    const sizes = c.model === 'google-omni' ? ['720p', '1080p', '2160p'] : c.model === 'minimax-h3' ? ['720p', '1440p'] : c.model === 'wan-3' ? ['720p', '1080p'] : c.model === 'seedance-2-5' ? ['480p', '720p', '1080p'] : ['480p', '720p'];
    if (!ratios.includes(c.aspectRatio) || !sizes.includes(c.resolution)) throw Error('Unsupported model settings.');
    if (c.model === 'google-omni' && ![4, 6, 8, 10].includes(c.duration)) throw Error('Omni duration must be 4, 6, 8 or 10 seconds.');
    if ((c.model === 'minimax-h3' || c.model.startsWith('grok-')) && c.duration > 15) throw Error('Selected model supports at most 15 seconds.');
    // Seedance/Wan long videos are split and merged by VideoCreationV1.
    return { config: c, task: { workflowId: 'SalesVideoPromptV3', input: {
      model: c.model, duration: c.duration, videoCount: c.count, aspectRatio: c.aspectRatio,
      resolution: c.resolution, generateAudio: c.generateAudio,
      referenceImages: [...c.productImages, ...c.creatorImages], creativeType: c.creativeType,
      salesRegion: c.targetCountry, speechLanguage: c.targetLanguage,
      productInfo: { name: c.productName ?? '', category: c.category ?? '', features: c.features ?? '',
        sellingPoints: c.sellingPoints ?? '', targetAudience: c.targetAudience ?? '', usageScenarios: c.usageScenarios ?? '' },
      creativeBrief: c.creativeRequirement,
    } } };
  }
  c.model ??= 'gpt-image-2-5-sunburst'; c.resolution ??= '1K'; c.count ??= 6;
  integer(c.count, 1, 10, 'image count');
  if (!['gpt-image-2-5-sunburst', 'gpt-image-2-5-flare'].includes(c.model) || !['1K', '2K', '4K'].includes(c.resolution)
    || !['9:16', '3:4', '4:5', '1:1', '16:9'].includes(c.aspectRatio)) throw Error('Unsupported frontend image settings.');
  if (c.productImages.length > 8) throw Error('Frontend image mode supports at most eight product images.');
  if (c.creativeMode && c.creativeMode !== 'original') throw Error('The shared frontend workflow supports original images only.');
  const sellingPoints = Array.isArray(c.sellingPoints) ? c.sellingPoints.join('\n') : c.sellingPoints ?? '';
  const name = c.productName?.trim() || sellingPoints.match(/(?:^|\n)\s*(?:产品名|Product name)\s*[:：]\s*([^\n]+)/i)?.[1]?.trim() || '';
  const points = sellingPoints.split('\n').map(line => line.trim()).filter(line => line && !/^(?:产品名|Product name)\s*[:：]/i.test(line));
  const editorSnapshot = { productName: c.productName ?? '', sellingPoints, targetAudience: c.targetAudience ?? '', creativeNotes: c.creativeRequirement,
    market: c.targetCountry, targetLanguage: c.targetLanguage, cardsPerSet: c.count,
    aspectRatio: c.aspectRatio, model: c.model, resolution: c.resolution,
    productImages: c.productImages, ...(c.creatorImages[0] ? { personImage: c.creatorImages[0] } : {}) };
  return { config: c, task: { workflowId: 'ProductImagePromptV1', editorSnapshot, input: {
    productBrief: { productName: name, sellingPoints: points,
      targetCountry: c.targetCountry, targetAudience: c.targetAudience?.trim() || '', productImages: c.productImages },
    creativeRequirement: c.creativeRequirement.trim(),
    userConfig: { creativeMode: 'original', cardsPerSet: c.count, aspectRatio: c.aspectRatio,
      targetLanguage: c.targetLanguage, storyStyle: 'storyDrivenCarousel', imageStyle: 'storyDrivenCarousel' },
    creatorBrief: { creatorMode: c.creatorImages.length ? 'provided' : 'none', creatorImages: c.creatorImages },
  } } };
}
function record(value) { return typeof value === 'string' ? JSON.parse(value) : value; }
export function generationTasks(plan, planning) {
  if (planning.status !== 'Succeeded' || !guid(planning.id)) throw Error('Planning has not succeeded.');
  const root = record(planning.output), payload = record(root?.output) ?? root;
  if (!payload || root.success === false || payload.success === false) throw Error('Planning output indicates failure.');
  const c = plan.config, images = [...c.productImages, ...c.creatorImages];
  if (c.kind === 'video') {
    const entries = Array.isArray(payload.videos) ? payload.videos : c.count === 1 ? [payload] : [];
    if (entries.length !== c.count) throw Error('Video plan count mismatch.');
    const seen = new Set();
    return entries.map((entry, index) => {
      const v = record(entry), p = record(v?.videoPrompt);
      if ((Array.isArray(payload.videos) && v.videoId !== index + 1) || p?.duration !== c.duration || !p?.prompt?.trim() || !p?.summary?.trim()) throw Error('Invalid full video plan.');
      const signature = p.prompt.replace(/\s+/g, '');
      if (seen.has(signature)) throw Error('Duplicate video plans.'); seen.add(signature);
      return { workflowId: 'VideoCreationV1', input: { taskType: 'reference', model: c.model, aspectRatio: c.aspectRatio,
        resolution: c.resolution, duration: c.duration, generateAudio: c.generateAudio, prompt: p.prompt, referenceImages: images },
        attributes: { saveGeneratedAssets: true, creationSource: 'commerce' } };
    });
  }
  const cards = record(payload.imagePrompts)?.cards;
  if (!Array.isArray(cards) || cards.length !== c.count) throw Error('Image plan count mismatch.');
  return cards.map((card, index) => {
    card = record(card);
    if (typeof card?.prompt !== 'string' || !card.prompt.trim()) throw Error('Empty card prompt.');
    const input = { model: c.model, prompt: card.prompt.trim(), aspectRatio: c.aspectRatio,
      resolution: c.resolution, referenceImages: images };
    return { workflowId: 'ImageGenV2', input, editorSnapshot: { workflowId: 'ImageGenV2',
      creationSource: 'shoppable-images', parentTaskId: planning.id, cardIndex: index, ...input }, attributes: { saveGeneratedAssets: true,
      creationSource: 'shoppable-images', parentTaskId: planning.id, cardIndex: index } };
  });
}

export class CommerceClient extends LuluLabClient {
  async upload(file) {
    const bytes = await readFile(file), mimeType = imageMimeType(bytes);
    if (!mimeType) throw Error('Upload requires a supported image file.');
    const ticket = await this.request('/uploads', { method: 'POST' });
    if (!guid(ticket.id)) throw Error('Upload ticket ID missing.');
    const form = new FormData();
    form.append('file', new Blob([bytes], { type: mimeType }), basename(file));
    const response = await this.fetch(url(ticket.presignedUrl), { method: 'POST', body: form,
      redirect: 'error', signal: AbortSignal.timeout(this.timeoutMs) });
    if (!response.ok) throw Error(`Upload HTTP ${response.status}.`);
    const result = await response.json();
    if (result.id !== ticket.id) throw Error('Uploaded file ID does not match ticket.');
    return { id: result.id, ...refs([result])[0] };
  }
}

async function save(file, state) {
  await mkdir(dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  await writeFile(tmp, JSON.stringify(state, null, 2) + '\n', { mode: 0o600 }); await rename(tmp, file);
}
async function load(file) { try { return JSON.parse(await readFile(file, 'utf8')); } catch (e) { if (e.code === 'ENOENT') return null; throw e; } }
async function locked(file, action) {
  await mkdir(dirname(file), { recursive: true }); const lock = `${file}.lock`;
  try { await mkdir(lock); } catch (e) { if (e.code === 'EEXIST') throw Error('State locked; verify the old process stopped before removing its lock.'); throw e; }
  try { return await action(); } finally { await rm(lock, { recursive: true }); }
}
async function createTask(state, slot, request, file, client) {
  if (slot.task?.id) return;
  if (slot.submissionUnknown) throw Error('Submission may already exist. Inspect owned task history; do not resubmit.');
  for (const files of [request.input?.referenceImages, request.input?.referenceAudios]) {
    for (const media of files ?? []) {
      const expiry = media.expiredAt || media.expiresAt;
      if (expiry && (!Number.isFinite(Date.parse(expiry)) || Date.parse(expiry) <= Date.now())) throw Error('Reference expired; no new task was submitted. Preserve the state and existing task IDs.');
    }
  }
  const quote = await client.request('/billing/quotes', { method: 'POST', body: request });
  if (!guid(quote?.id)) throw Error('Quote ID missing.');
  slot.request = request; slot.quoteId = quote.id; slot.submissionUnknown = true;
  await save(file, state);
  const task = await client.request('/tasks', { method: 'POST', body: { ...request, quoteId: quote.id } });
  if (!guid(task?.id)) throw Error('Task ID missing; inspect history before recovery.');
  slot.task = task; slot.submissionUnknown = false; await save(file, state);
}
export async function submit(config, file, client) {
  const plan = buildPlan(config), signature = createHash('sha256').update(JSON.stringify(plan)).digest('hex');
  return locked(file, async () => {
    let state = await load(file);
    if (state && (state.schema !== SCHEMA || state.signature !== signature)) throw Error('State belongs to another request or legacy task.');
    state ??= { schema: SCHEMA, signature, plan, planning: {}, generations: [] };
    await createTask(state, state.planning, plan.task, file, client); return state;
  });
}
export async function advance(file, client, approved = false) {
  return locked(file, async () => {
    const state = await load(file);
    if (state?.schema !== SCHEMA) throw Error('No saved commerce state.');
    for (const slot of [state.planning, ...state.generations]) {
      if (slot.submissionUnknown && !slot.task?.id) throw Error('Uncertain submission; inspect history before recovery.');
      if (slot.task?.id && !terminal(slot.task)) { slot.task = await client.task(slot.task.id); await save(file, state); }
    }
    if (approved && state.planning.task?.status === 'Succeeded') {
      const requests = generationTasks(state.plan, state.planning.task);
      for (const [index, request] of requests.entries()) {
        state.generations[index] ??= {};
        await createTask(state, state.generations[index], request, file, client);
      }
    }
    return state;
  });
}
export function estimateItems(plan) {
  if (plan.config.kind !== 'image') throw Error('Image estimates require kind=image.');
  const { model, resolution, count: imageCount } = plan.config;
  return [{ workflowId: 'ProductImagePromptV1' }, { workflowId: 'ImageGenV2', input: { model, resolution, imageCount } }];
}

export async function estimate(config, client) {
  const result = await client.request('/billing/estimates', { method: 'POST', body: { items: estimateItems(buildPlan(config)) } });
  if (!Number.isSafeInteger(result?.credits) || result.credits < 0) throw Error('Billing estimate has no valid credit total. Do not submit.');
  return result;
}

export async function main(args = process.argv.slice(2)) {
  if (!args.length || args.includes('--help')) {
    process.stdout.write('Dispatcher commerce: upload --file PATH --output asset.json; plan --config request.json; estimate --config request.json; submit --config request.json --state state.json --generation-approved; advance --state state.json --generation-approved; poll --state state.json; download --state state.json --output DIR\nplan is offline; poll only reads tasks; advance submits missing generation tasks under the original approval.\n'); return;
  }
  const command = args[0], allowed = { upload: ['--file', '--output'], plan: ['--config'], estimate: ['--config'], submit: ['--config', '--state', '--generation-approved'], advance: ['--state', '--generation-approved'], poll: ['--state'], download: ['--state', '--output'] };
  if (!allowed[command]) throw Error('Unknown command.');
  const flags = {};
  for (let i = 1; i < args.length; i++) {
    const flag = args[i];
    if (!allowed[command].includes(flag) || Object.hasOwn(flags, flag)) throw Error('Unknown or repeated flag.');
    if (flag === '--generation-approved') flags[flag] = true;
    else { if (!args[i + 1] || args[i + 1].startsWith('--')) throw Error('Missing flag value.'); flags[flag] = args[++i]; }
  }
  const path = name => { if (!flags[name]) throw Error(`Missing ${name}.`); return resolve(flags[name]); };
  if (['submit', 'advance'].includes(command) && !flags['--generation-approved']) throw Error('Existing user authorization is required.');
  const config = ['plan', 'estimate', 'submit'].includes(command) ? JSON.parse(await readFile(path('--config'), 'utf8')) : null;
  if (command === 'plan') { process.stdout.write(JSON.stringify(buildPlan(config), null, 2) + '\n'); return; }
  const stateFile = ['submit', 'advance', 'poll', 'download'].includes(command) ? path('--state') : null;
  const output = ['upload', 'download'].includes(command) ? path('--output') : null;
  const source = command === 'upload' ? path('--file') : null;
  const client = new CommerceClient({ apiKey: await resolveApiKey(), baseUrl: process.env.LULULAB_API_BASE_URL || 'https://customer.lululab.ai' });
  let state;
  if (command === 'estimate') {
    state = await estimate(config, client);
  }
  else if (command === 'upload') { const asset = await client.upload(source); await save(output, asset); state = asset; }
  else if (command === 'submit') state = await submit(config, stateFile, client);
  else if (command === 'advance' || command === 'poll') state = await advance(stateFile, client, command === 'advance');
  else {
    state = await locked(stateFile, async () => {
      const s = await load(stateFile);
      if (s?.schema !== SCHEMA) throw Error('No saved commerce state.');
      await mkdir(output, { recursive: true });
      for (const [index, slot] of s.generations.entries()) {
        if (slot.task?.status !== 'Succeeded') continue;
        const payload = record(slot.task.output), video = s.plan.config.kind === 'video';
        const result = video ? payload?.video : payload?.image ?? payload?.images?.[0];
        const address = url(typeof result === 'string' ? result : result?.url);
        const response = await client.fetch(address, { redirect: 'error', signal: AbortSignal.timeout(180000) });
        if (!response.ok) throw Error(`Download HTTP ${response.status}.`);
        const bytes = Buffer.from(await response.arrayBuffer());
        if (!bytes.length) throw Error('Empty output.');
        const mime = response.headers.get('content-type')?.split(';')[0];
        const extension = video ? 'mp4' : ({ 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp' }[mime]);
        if (!extension) throw Error('Unsupported output media type.');
        slot.file = resolve(output, `${video ? 'video' : 'card'}_${String(index + 1).padStart(2, '0')}.${extension}`);
        await writeFile(slot.file, bytes); await save(stateFile, s);
      }
      return s;
    });
  }
  process.stdout.write(JSON.stringify(state, null, 2) + '\n');
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
