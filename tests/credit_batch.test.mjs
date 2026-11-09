import test from 'node:test';
import assert from 'node:assert/strict';

const skill = 'LuluLab-Product-Image';
const { LuluLabClient } = await import('../scripts/lululab_cli.mjs');
{
  test(`${skill}: a 66-credit batch with 53 available makes no task POST`, async () => {
    const calls = [];
    const client = new LuluLabClient({ apiKey: 'test', fetchImpl: async (url, options) => {
      const path = new URL(url).pathname; calls.push(path);
      if (path === '/billing/quotes') {
        const duration = JSON.parse(options.body).input.duration;
        return Response.json({ id: `quote-${duration}`, credits: duration * 3 });
      }
      assert.equal(path, '/credits');
      return Response.json({ total: 1, items: [{ creditsBalance: 100, creditsReserved: 47 }] });
    }});
    await assert.rejects(client.submitBatch([12, 10].map(duration => ({ workflowId: 'VideoGenV2', input: { duration } }))), error => error.code === 'LULULAB_CREDITS_INSUFFICIENT');
    assert.deepEqual(calls, ['/billing/quotes', '/billing/quotes', '/credits']);
  });
  test(`${skill}: exact funds send all segments together, with no individual fallback`, async () => {
    const calls = [];
    const client = new LuluLabClient({ apiKey: 'test', fetchImpl: async (url, options) => {
      const path = new URL(url).pathname; calls.push(path);
      if (path === '/billing/quotes') {
        const duration = JSON.parse(options.body).input.duration;
        return Response.json({ id: `quote-${duration}`, credits: duration * 3 });
      }
      if (path === '/credits') return Response.json({ total: 1, items: [{ creditsAvailable: 66 }] });
      assert.equal(path, '/tasks/batch');
      assert.equal(JSON.parse(options.body).length, 2);
      return Response.json([{ id: 'segment-1' }, { id: 'segment-2' }]);
    }});
    const result = await client.submitBatch([12, 10].map(duration => ({ workflowId: 'VideoGenV2', input: { duration } })));
    assert.equal(result.length, 2);
    assert.deepEqual(calls, ['/billing/quotes', '/billing/quotes', '/credits', '/tasks/batch']);
  });
}
