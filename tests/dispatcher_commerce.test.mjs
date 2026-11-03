import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildPlan, generationTasks, estimateItems, submit, advance } from '../scripts/dispatcher_commerce.mjs';

const product = { url: 'https://assets.example/product.png', mimeType: 'image/png' };
const creator = { url: 'https://assets.example/creator.png', mimeType: 'image/png' };
const id = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const config = { kind: 'image', productImages: [product] };
const output = count => ({ success: true, output: JSON.stringify({ imagePrompts: { cards: Array.from({ length: count }, (_, index) => ({ title: `Card ${index}`, prompt: `  Original prompt ${index}  `, textOverlay: 'Overlay' })) } }) });

test('frontend defaults, product facts, creator references and editor snapshot', () => {
  const plan = buildPlan({ ...config, sellingPoints: ' 产品名：沐浴露\n 滋润肌肤 \n\n', targetAudience: ' 年轻女性 ', creativeRequirement: ' 保留包装 ', creatorImages: [creator] });
  assert.equal(plan.config.count, 6);
  assert.deepEqual(plan.task.input, {
    productBrief: { productName: '沐浴露', sellingPoints: ['滋润肌肤'], targetCountry: 'United States', targetAudience: '年轻女性', productImages: [product] },
    creativeRequirement: '保留包装',
    userConfig: { creativeMode: 'original', cardsPerSet: 6, aspectRatio: '9:16', targetLanguage: 'en-US', storyStyle: 'storyDrivenCarousel', imageStyle: 'storyDrivenCarousel' },
    creatorBrief: { creatorMode: 'provided', creatorImages: [creator] },
  });
  assert.equal(plan.task.editorSnapshot.cardsPerSet, 6);
  assert.equal(plan.task.editorSnapshot.model, 'gpt-image-2-5-sunburst');
  assert.equal(plan.task.editorSnapshot.sellingPoints.includes('滋润肌肤'), true);
  assert.deepEqual(plan.task.editorSnapshot.personImage, creator);
  assert.equal(buildPlan(config).task.input.creatorBrief.creatorMode, 'none');
  assert.deepEqual(buildPlan(config).task.input.productBrief.sellingPoints, []);
});

test('frontend reference and count constraints reject before billing', () => {
  assert.throws(() => buildPlan({ ...config, count: 11 }));
  assert.throws(() => buildPlan({ ...config, productImages: Array(9).fill(product) }));
  assert.throws(() => buildPlan({ ...config, creatorImages: [creator, creator] }));
  assert.throws(() => buildPlan({ ...config, productImages: [{ ...product, expiredAt: '2020-01-01T00:00:00Z' }] }));
  assert.throws(() => buildPlan({ ...config, creativeMode: 'benchmarkCarousel' }));
  const file = { location: product.url, mimeType: product.mimeType, expiresAt: '2099-01-01T00:00:00Z' };
  assert.deepEqual(buildPlan({ ...config, productImages: [file] }).config.productImages, [{ ...product, expiredAt: file.expiresAt }]);
});

test('cards use original prompts, frontend generation attributes and full-set estimates', () => {
  const plan = buildPlan({ ...config, creatorImages: [creator], count: 2, resolution: '2K' });
  const tasks = generationTasks(plan, { id: id(1), status: 'Succeeded', output: output(2) });
  assert.deepEqual(tasks.map(task => task.input.prompt), ['Original prompt 0', 'Original prompt 1']);
  assert.deepEqual(tasks[1].input.referenceImages, [product, creator]);
  assert.deepEqual(tasks[1].attributes, { saveGeneratedAssets: true, creationSource: 'shoppable-images', parentTaskId: id(1), cardIndex: 1 });
  assert.equal(tasks[1].editorSnapshot.cardIndex, 1);
  assert.deepEqual(estimateItems(plan), [{ workflowId: 'ProductImagePromptV1' }, { workflowId: 'ImageGenV2', input: { model: 'gpt-image-2-5-sunburst', resolution: '2K', imageCount: 2 } }]);
  assert.throws(() => generationTasks(plan, { id: id(1), status: 'Succeeded', output: output(1) }), /count mismatch/);
  assert.throws(() => generationTasks(plan, { id: id(1), status: 'Succeeded', output: { success: false } }));
});

test('quote then submit, read-only poll, and resume without duplicate paid tasks', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lululab-image-'));
  const file = join(dir, 'state.json');
  const calls = [];
  let sequence = 0;
  const client = {
    async request(path, options) {
      calls.push({ path, ...options });
      if (path === '/billing/quotes') return { id: id(90) };
      const saved = JSON.parse(await readFile(file, 'utf8'));
      const slot = sequence === 0 ? saved.planning : saved.generations[sequence - 1];
      assert.equal(slot.submissionUnknown, true);
      assert.equal(options.body.quoteId, id(90));
      return { id: id(++sequence), status: 'Pending' };
    },
    async task(taskId) { return { id: taskId, status: taskId === id(3) ? 'Failed' : 'Succeeded', output: taskId === id(1) ? output(2) : { images: [product] } }; },
  };
  try {
    await submit({ ...config, count: 2 }, file, client);
    await advance(file, client, false);
    assert.equal(calls.length, 2);
    await advance(file, client, true);
    assert.deepEqual(calls.map(call => call.path), Array(3).fill(['/billing/quotes', '/tasks']).flat());
    const state = await advance(file, client, true);
    assert.equal(state.generations[1].task.status, 'Failed');
    assert.equal(calls.length, 6);
    await submit({ ...config, count: 2 }, file, client);
    assert.equal(calls.length, 6);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('unknown submission remains saved and blocks a paid resubmission', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lululab-image-unknown-'));
  const file = join(dir, 'state.json');
  let posts = 0;
  const client = { async request(path) { if (path === '/billing/quotes') return { id: id(90) }; posts++; throw Error('Lost response'); } };
  try {
    await assert.rejects(submit(config, file, client), /Lost response/);
    await assert.rejects(submit(config, file, client), /may already exist/);
    assert.equal(posts, 1);
    assert.equal(JSON.parse(await readFile(file, 'utf8')).planning.submissionUnknown, true);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('resume refuses expired references without new quotes and retains the planning ID', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lululab-expired-')), file = join(dir, 'state.json');
  let requests = 0;
  const client = { async request(path) { requests++; return { id: id(path === '/tasks' ? 1 : 90), status: 'Pending' }; },
    async task() { return { id: id(1), status: 'Succeeded', output: output(1) }; } };
  const originalNow = Date.now;
  try {
    const expires = originalNow() + 60000;
    await submit({ ...config, count: 1, productImages: [{ ...product, expiredAt: new Date(expires).toISOString() }] }, file, client);
    Date.now = () => expires + 1;
    await assert.rejects(advance(file, client, true), /Reference expired/);
    assert.equal(requests, 2);
    assert.equal(JSON.parse(await readFile(file, 'utf8')).planning.task.id, id(1));
  } finally { Date.now = originalNow; await rm(dir, { recursive: true, force: true }); }
});
