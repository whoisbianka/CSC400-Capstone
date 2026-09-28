// Run with: node --test tests/test_program_api.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(enabled, fetch) {
  const window = {
    DEMO_API_ENABLED: enabled,
    programCatalog: { getPrograms: () => [], isDemo: () => true, setPrograms() {} },
    demoSearch: () => ({ rows: [{ id: 'browser-result' }], filters: [], terms: [] })
  };
  vm.runInNewContext(fs.readFileSync('assets/js/program-api.js', 'utf8'), {
    window, fetch, AbortController, setTimeout, clearTimeout,
    document: { getElementById: () => null }
  });
  return window.programApi;
}

test('static hosting uses browser search without API requests', async () => {
  const api = setup(false, () => { throw new Error('Unexpected fetch'); });
  const result = await api.search('computer science');
  assert.equal(result.rows[0].id, 'browser-result');
  assert.equal(result.demo, true);
});

test('Python mode sends the question as JSON and returns server results', async () => {
  const calls = [];
  const api = setup(true, async (path, options) => {
    calls.push({ path, options });
    return { ok: true, json: async () => path === '/api/programs'
      ? { programs: [], demo: true } : { rows: [{ id: 'python-result' }], demo: true, engine: 'python' } };
  });
  const result = await api.search('computer science');
  const call = calls.find(call => call.path === '/api/search');
  assert.equal(call.options.method, 'POST');
  assert.deepEqual(JSON.parse(call.options.body), { question: 'computer science' });
  assert.equal(result.engine, 'python');
  assert.equal(result.rows[0].id, 'python-result');
});

test('Python failures reject instead of silently using browser matches', async () => {
  const api = setup(true, async () => ({ ok: false, status: 503 }));
  await assert.rejects(api.search('computer science'), /503/);
});
