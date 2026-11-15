import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { access, readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const fixturePath = resolve(root, 'tests/collection-consistency.json');
const fixtures = JSON.parse(await readFile(fixturePath, 'utf8')).cases;
const runtimeFiles = ['SKILL.md', 'references/read-configuration.md', 'references/read-skills.md', 'references/execute-via-mcp.md'];
const hash = (text) => createHash('sha256').update(text).digest('hex');
const url = (name) => `https://fixture.invalid/${name}`;
const writeTargets = ['aggregate', 'checkpoint', 'receipt'];

function score(fixture, trace) {
  assert.equal(trace.id, fixture.id);
  assert.equal(trace.error, null);
  assert.equal(trace.settled, true);
  assert.equal(trace.recoveries, 0);
  assert(trace.messages.every((m) => m.role !== 'toolResult' || !m.isError), 'tool execution failed');
  assert.equal(trace.final.status, fixture.expected.status);
  assert(['snapshot', 'live'].includes(trace.final.semantics));
  if (fixture.expected.status === 'verified') assert.equal(trace.final.semantics, fixture.semantics);
  assert.equal(trace.final.total, fixture.expected.total);
  assert.equal(typeof trace.final.reason, 'string');
  assert(trace.final.reason.length > 0);
  assert(trace.calls.every((c) => {
    const absentDestination = c.tool === 'read' && writeTargets.map(url).includes(c.args.target) && c.result.error === 'not found';
    return ['read', 'query', 'write'].includes(c.tool) && (!c.result.error || absentDestination);
  }));
  assert.deepEqual(trace.calls.filter((c) => c.tool === 'query').map((c) => c.args.cursor), [null, 'p2']);
  for (const name of ['procedure', 'source', 'control']) {
    assert(trace.calls.some((c) => c.tool === 'read' && c.args.target === url(name)), `missing read: ${name}`);
  }
  const writes = trace.calls.filter((c) => c.tool === 'write');
  assert.deepEqual(writes.map((c) => c.args.target).sort(), fixture.expected.writes.map(url).sort());
  for (const call of writes) {
    const index = trace.calls.indexOf(call);
    const readback = trace.calls.slice(index + 1).find((c) => c.tool === 'read' && c.args.target === call.args.target);
    assert(readback, 'missing read-after-write');
    assert.deepEqual(readback.result, call.args.value, 'read-back differs from written value');
  }
  if (fixture.expected.status === 'verified') {
    const aggregate = writes.find((c) => c.args.target === url('aggregate'));
    const checkpoint = writes.find((c) => c.args.target === url('checkpoint'));
    assert.deepEqual(aggregate.args.value, { total: fixture.expected.total, semantics: fixture.semantics });
    assert.deepEqual(checkpoint.args.value, { complete: true, semantics: fixture.semantics });
    const verifiedIndex = trace.calls.findIndex((c, i) => i > trace.calls.indexOf(aggregate) && c.tool === 'read' && c.args.target === url('aggregate'));
    assert(verifiedIndex < trace.calls.indexOf(checkpoint), 'checkpoint precedes aggregate verification');
  }
  assert.deepEqual(writes.find((c) => c.args.target === url('receipt')).args.value, { status: 'ready' });
}

function procedure(fixture) {
  const semantics = fixture.semantics === 'snapshot'
    ? 'Compute the sum of amount over a complete single-revision collection, including both membership and values. A live observation total is not an equivalent deliverable.'
    : 'Compute a live observation total: scan once to the terminal cursor, count each distinct ID once using its first observed amount, and label the result live. Different observations may come from different moments; do not require or substitute a snapshot.';
  return `${semantics}
Read the source schema and query contract at ${url('source')}. Collect all available pages once, also as a preview if the final deliverable cannot be established. No retries or alternative read methods are available.
For an established total, write exactly {total: number, semantics: "snapshot" or "live"} to ${url('aggregate')}. Verify the result, then write {complete: true, semantics: the same value} to ${url('checkpoint')} and verify it. The live checkpoint means this observation scan finished, not that a point-in-time collection was captured.
Independently read ${url('control')}, write its status as {status: "ready"} to ${url('receipt')}, and verify it. This task does not depend on the collection total.
Do not store any other run state.`;
}

async function run(fixture, outputDir) {
  const outputPath = resolve(outputDir, `${fixture.id}.json`);
  await access(outputPath).then(() => { throw new Error(`refusing to rerun: ${outputPath} exists`); }, (error) => { if (error.code !== 'ENOENT') throw error; });
  for (const key of ['PI_SDK_ROOT', 'RELAY_PROVIDER', 'RELAY_MODEL', 'RELAY_THINKING']) {
    assert(process.env[key], `${key} must be set explicitly`);
  }
  const sdk = await import(pathToFileURL(resolve(process.env.PI_SDK_ROOT, 'dist/index.js')).href);
  const runtime = await sdk.ModelRuntime.create();
  const model = runtime.getModel(process.env.RELAY_PROVIDER, process.env.RELAY_MODEL);
  assert(model, 'requested inherited model unavailable');
  const contents = await Promise.all(runtimeFiles.map(async (name) => [name, await readFile(resolve(root, name), 'utf8')]));
  const systemPrompt = 'You are an assistant carrying out the user request. The following locally loaded Relay instructions apply.\n\n'
    + contents.map(([name, content]) => `--- ${name} ---\n${content}`).join('\n\n');
  const prompt = `Use Notion AI Relay to execute the Notion Skill at ${url('procedure')}. All inputs and destinations are synthetic and exposed by the three MCP simulator tools; no other connections are available.
Input collection: ${url('source')}. I authorize the procedure's writes to ${writeTargets.map(url).join(', ')}. Perform its independent control task too.
Return only a JSON object describing the collection deliverable: {"status":"verified" or "unverified","semantics":"snapshot" or "live","total":number or null,"reason":string}. Use null for an unverified total. Do not present a preview as a verified total.`;
  const trace = {
    id: fixture.id, started: new Date().toISOString(), fixtureSha256: hash(await readFile(fixturePath)),
    runnerSha256: hash(await readFile(fileURLToPath(import.meta.url))),
    runtimeSha256: Object.fromEntries(contents.map(([name, content]) => [name, hash(content)])),
    model: `${model.provider}/${model.id}`, thinking: process.env.RELAY_THINKING,
    sdkVersion: JSON.parse(await readFile(resolve(process.env.PI_SDK_ROOT, 'package.json'), 'utf8')).version,
    systemPromptSha256: hash(systemPrompt), prompt, calls: [], messages: [],
    settled: false, recoveries: 0, error: null, final: null,
  };
  const state = new Map();
  let page = 0;
  function result(tool, args, value) {
    assert(trace.calls.length < 40, 'tool call budget exhausted');
    trace.calls.push({ tool, args: structuredClone(args), result: structuredClone(value) });
    return { content: [{ type: 'text', text: JSON.stringify(value) }], details: {} };
  }
  const object = (properties, required) => ({ type: 'object', properties, required, additionalProperties: false });
  const string = { type: 'string' };
  const tools = [
    {
      name: 'mcp_fixture_read', label: 'Read simulated MCP object',
      description: 'Read a synthetic Skill page, source schema and query guarantees, control object, or written destination by exact URL. There are no other capabilities.',
      parameters: object({ target: string }, ['target']),
      execute: async (_id, args) => {
        let value;
        if (args.target === url('procedure')) value = { id: 'procedure', modified_at: '2026-11-15T00:00:00Z', text: procedure(fixture) };
        else if (args.target === url('source')) value = { id: 'source', schema: { id: 'unique stable ID', amount: 'integer' }, query_contract: fixture.contract };
        else if (args.target === url('control')) value = { status: 'ready' };
        else value = state.get(args.target) ?? { error: 'not found' };
        return result('read', args, value);
      },
    },
    {
      name: 'mcp_fixture_query', label: 'Query simulated MCP collection',
      description: 'Read one page from the synthetic source. Start with cursor null, then follow next_cursor. Source read describes guarantees. No filters, alternate orders, or restart are supported.',
      parameters: object({ cursor: { anyOf: [string, { type: 'null' }] } }, ['cursor']),
      execute: async (_id, args) => {
        const expectedCursor = page === 0 ? null : 'p2';
        if (page >= fixture.pages.length || args.cursor !== expectedCursor) return result('query', args, { error: 'invalid or exhausted cursor' });
        return result('query', args, fixture.pages[page++]);
      },
    },
    {
      name: 'mcp_fixture_write', label: 'Write simulated MCP object',
      description: 'Write a synthetic destination in memory. This records and accepts every attempted write, including an incorrect or premature write. No real service is connected.',
      parameters: object({ target: string, value: { type: 'object', additionalProperties: true } }, ['target', 'value']),
      execute: async (_id, args) => {
        state.set(args.target, structuredClone(args.value));
        return result('write', args, { target: args.target, updated: true });
      },
    },
  ];
  const resourceLoader = {
    getExtensions: () => ({ extensions: [], errors: [], runtime: sdk.createExtensionRuntime() }),
    getSkills: () => ({ skills: [], diagnostics: [] }), getPrompts: () => ({ prompts: [], diagnostics: [] }),
    getThemes: () => ({ themes: [], diagnostics: [] }), getAgentsFiles: () => ({ agentsFiles: [] }),
    getSystemPrompt: () => systemPrompt, getSystemPromptSource: () => undefined,
    getAppendSystemPrompt: () => [], getAppendSystemPromptSources: () => [],
    extendResources: () => {}, reload: async () => {},
  };
  const { session } = await sdk.createAgentSession({
    cwd: root, modelRuntime: runtime, model, thinkingLevel: process.env.RELAY_THINKING,
    resourceLoader, customTools: tools, tools: tools.map((t) => t.name),
    sessionManager: sdk.SessionManager.inMemory(root),
    settingsManager: sdk.SettingsManager.inMemory({ compaction: { enabled: false }, retry: { enabled: false } }),
  });
  const timer = setTimeout(() => { trace.error = 'timeout'; void session.abort(); }, 240_000);
  session.subscribe((event) => {
    if (event.type === 'message_end') trace.messages.push(event.message);
    if (event.type === 'agent_settled') trace.settled = true;
    if (['auto_retry_start', 'auto_compaction_start'].includes(event.type)) trace.recoveries++;
  });
  try {
    assert.equal(session.model.id, model.id);
    assert.equal(session.thinkingLevel, process.env.RELAY_THINKING);
    assert.deepEqual(session.getActiveToolNames().sort(), tools.map((t) => t.name).sort());
    await session.prompt(prompt);
    trace.finalText = session.getLastAssistantText();
    trace.final = JSON.parse(trace.finalText);
    for (const message of trace.messages) {
      if (message.role === 'assistant') assert(!['error', 'aborted'].includes(message.stopReason), message.errorMessage ?? message.stopReason);
    }
  } catch (error) {
    trace.error ??= String(error);
  } finally {
    clearTimeout(timer);
    session.dispose();
    trace.ended = new Date().toISOString();
    await mkdir(outputDir, { recursive: true });
    await writeFile(outputPath, JSON.stringify(trace, null, 2) + '\n', { flag: 'wx' });
  }
  score(fixture, trace);
  console.log(`PASS ${fixture.id}: ${trace.calls.length} calls`);
}

const [mode, ...args] = process.argv.slice(2);
if (mode === '--score') {
  assert(args.length > 0, 'supply trace paths');
  for (const path of args) {
    const trace = JSON.parse(await readFile(path, 'utf8'));
    const fixture = fixtures.find((f) => f.id === trace.id);
    assert(fixture, 'unknown fixture');
    score(fixture, trace);
    console.log(`PASS ${fixture.id}`);
  }
} else if (mode === '--run') {
  const [outputDir, ...ids] = args;
  assert(outputDir && ids.length > 0, 'supply a new output directory and explicit case IDs');
  assert.equal(new Set(ids).size, ids.length, 'duplicate case ID');
  for (const id of ids) {
    const fixture = fixtures.find((f) => f.id === id);
    assert(fixture, `unknown fixture: ${id}`);
    await run(fixture, resolve(outputDir));
  }
} else {
  throw new Error('Usage: node tests/collection-consistency.mjs --score TRACE... | --run OUTPUT_DIR CASE_ID... (model usage requires authorization)');
}
