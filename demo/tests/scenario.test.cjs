const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { steps, flows, stateAt, version } = require('../src/scenario.js');
const root = path.resolve(__dirname, '../..');
const ids = steps.map(step => step.id);
const at = id => stateAt(ids.indexOf(id));

test('the single recovery story follows the actual event, job, MCP, reasoning, execution, and verification order', () => {
  assert.deepEqual(ids, ['healthy','failure','detected','event','matched','investigation-job','agent-awake','monitoring-investigation','linux-investigation','aap-investigation','reasoning','discover','request','execute','job-success','verify','recovered']);
  assert.equal(new Set(ids).size, steps.length);
  assert.match(steps.find(s => s.id === 'request').description, /Deploy Zabbix Agent/);
});

test('an event cannot wake the agent before the AAP investigation job', () => {
  for (const id of ['healthy','failure','detected','event','matched','investigation-job']) assert.equal(at(id).agent, 'idle');
  assert.equal(at('agent-awake').investigationJob, 'running');
  const wake = flows.find(f => f.id === 'wake');
  assert.equal(wake.from, 'controller');
  assert.equal(wake.to, 'agent');
  assert.equal(wake.kind, 'dispatch');
});

test('every AI system interaction passes through an MCP interface', () => {
  for (const flow of flows.filter(f => f.from === 'agent' || f.to === 'agent')) {
    if (flow.id === 'wake') continue;
    assert.match(flow.from === 'agent' ? flow.to : flow.from, /-mcp$/);
    assert.ok(['read','request'].includes(flow.kind));
  }
  for (const [stepId, expected] of [['monitoring-investigation',['ai-zabbix','mcp-zabbix']], ['linux-investigation',['ai-linux','mcp-linux']], ['aap-investigation',['ai-aap','mcp-aap']]]) {
    assert.deepEqual(at(stepId).step.flows, expected);
    assert.ok(expected.every(id => flows.find(f => f.id === id).kind === 'read'));
  }
  assert.deepEqual(at('request').step.flows.slice(0,2), ['ai-aap-request','mcp-aap-request']);
});

test('only AAP originates the path that changes the managed server', () => {
  const writes = flows.filter(f => f.kind === 'execute');
  assert.equal(writes.length, 1);
  assert.equal(writes[0].from, 'controller');
  assert.equal(writes[0].to, 'server');
  assert.deepEqual(at('execute').step.flows, ['execute']);
  assert.equal(at('request').server, 'missing');
});

test('reasoning follows all three investigations and precedes catalog discovery and job launch', () => {
  assert.equal(at('aap-investigation').rootCause, false);
  assert.equal(at('reasoning').agent, 'reasoning');
  assert.equal(at('reasoning').rootCause, true);
  assert.equal(at('reasoning').step.evidence.length, 3);
  assert.deepEqual(at('reasoning').step.flows, []);
  assert.equal(at('reasoning').server, 'missing');
  assert.equal(at('discover').remediationJob, 'ready');
});

test('a successful AAP job cannot mark monitoring recovered without a subsequent check', () => {
  assert.equal(at('job-success').remediationJob, 'successful');
  assert.equal(at('job-success').server, 'restored');
  assert.equal(at('job-success').monitoring, 'problem');
  assert.equal(at('job-success').monitoringPending, true);
  assert.equal(at('verify').monitoring, 'healthy');
  assert.ok(at('verify').step.flows.includes('checks'));
  assert.ok(at('verify').step.flows.includes('ai-zabbix'));
  assert.equal(at('recovered').server, 'healthy');
});

test('monitoring detects the package failure after its last healthy observation', () => {
  assert.equal(at('failure').monitoring, 'healthy');
  assert.equal(at('failure').monitoringPending, true);
  assert.equal(at('detected').monitoring, 'problem');
});

test('jumping backwards and restarting reconstruct the complete state without retained incident state', () => {
  const before = stateAt(0);
  for (let i = 0; i < steps.length; i++) stateAt(i);
  assert.deepEqual(stateAt(0), before);
  assert.equal(at('linux-investigation').server, 'missing');
  assert.equal(at('linux-investigation').remediationJob, 'ready');
  assert.ok(Object.isFrozen(before.step));
  assert.ok(Object.isFrozen(before.evidence));
  for (const value of [-1, steps.length, 1.5, NaN, '1', null]) assert.throws(() => stateAt(value), RangeError);
});

test('all technical sources resolve to existing tracked repository files and all flows have defined endpoints', () => {
  const nodes = new Set(['server','zabbix','agent','eda','controller','catalog','linux-mcp','zabbix-mcp','aap-mcp']);
  for (const step of steps) {
    assert.ok(fs.existsSync(path.join(root, step.source)), step.source);
    assert.ok(step.excerpt.length > 0);
    assert.ok(step.active.every(id => nodes.has(id)));
    assert.ok(step.flows.every(id => flows.some(flow => flow.id === id)));
  }
  for (const flow of flows) { assert.ok(nodes.has(flow.from)); assert.ok(nodes.has(flow.to)); }
});

test('the page is self-contained and its EDA is structurally inside AAP', () => {
  const html = fs.readFileSync(path.join(root, 'demo/index.html'), 'utf8');
  for (const match of html.matchAll(/<(?:script|link)\b[^>]*(?:src|href)="([^"]+)"/g)) {
    assert.ok(!/^https?:/.test(match[1]), `External runtime dependency: ${match[1]}`);
    assert.ok(fs.existsSync(path.join(root, 'demo', match[1])));
  }
  assert.match(html, /id="node-eda" class="component platform-node/);
  assert.match(html, /Functionality demo/);
  assert.match(html, /hardening work remains/);
  assert.match(html, /not a proof of enforced isolation/);
  assert.match(version, /^\d+\.\d+\.\d+$/);
  assert.match(html, new RegExp(`v${version.replaceAll('.', '\\.')}`));
  const code = fs.readFileSync(path.join(root, 'demo/src/app.js'), 'utf8');
  assert.doesNotMatch(code, /\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|localStorage|sessionStorage/);
});
