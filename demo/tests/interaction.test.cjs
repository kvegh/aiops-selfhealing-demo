// Minimal DOM harness for actual app handlers; this does not verify browser layout.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const model = require('../src/scenario.js');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const appCode = fs.readFileSync(path.join(__dirname, '../src/app.js'), 'utf8');

function harness({ reducedMotion = false, hash = '' } = {}) {
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag; this.children = []; this.attributes = {}; this.dataset = {}; this.style = {}; this.listeners = {};
      this.textContent = ''; this.scrollTop = 0; this.clientHeight = 600; this.offsetHeight = 30;
      this.classList = { values: new Set(), add: (...v) => v.forEach(x => this.classList.values.add(x)), remove: (...v) => v.forEach(x => this.classList.values.delete(x)), toggle: (v, yes) => yes ? this.classList.values.add(v) : this.classList.values.delete(v) };
    }
    setAttribute(k, v) { this.attributes[k] = String(v); }
    getAttribute(k) { return this.attributes[k]; }
    removeAttribute(k) { delete this.attributes[k]; }
    append(...children) { this.children.push(...children); }
    addEventListener(k, handler) { (this.listeners[k] ||= []).push(handler); }
    querySelector(k) { return this.children.find(c => c.tagName === k); }
    closest() { return null; }
    getBoundingClientRect() { return { top: 0 }; }
    showModal() { this.open = true; }
    close() { this.open = false; }
    click() { if (!this.disabled) for (const handler of this.listeners.click || []) handler({ target: this }); }
  }
  const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(m => [m[1], new Element()]));
  for (const match of html.matchAll(/<g id="(node-[^"]+)"/g)) elements.get(match[1]).id = match[1];
  elements.get('next').append(new Element('small'));
  const app = new Element();
  const document = new Element();
  document.getElementById = id => { assert.ok(elements.has(id), `Unknown element ${id}`); return elements.get(id); };
  document.createElement = tag => new Element(tag);
  document.createElementNS = (_, tag) => new Element(tag);
  document.querySelector = selector => selector === '.app' ? app : null;
  document.querySelectorAll = () => [...elements.values()].filter(e => e.id?.startsWith('node-'));
  const window = new Element();
  const location = { hash };
  const media = new Element(); media.matches = reducedMotion;
  const context = { document, window, location, history: { replaceState: (_, __, value) => { location.hash = value; } }, matchMedia: () => media, URLSearchParams, AIOpsDemo: model };
  vm.runInNewContext(appCode, context);
  const key = value => { for (const handler of document.listeners.keydown) handler({ key: value, target: app, preventDefault() {} }); };
  return { app, elements, key, location };
}

test('actual Next/Previous/Restart handlers traverse the story and retain unresolved monitoring after job success', () => {
  const { app, elements } = harness();
  assert.equal(app.dataset.step, 'healthy');
  assert.equal(elements.get('previous').disabled, true);
  for (const step of model.steps.slice(1)) {
    elements.get('next').click();
    assert.equal(app.dataset.step, step.id);
    assert.equal(elements.get('current-title').textContent, step.title);
    if (step.id === 'job-success') {
      assert.equal(elements.get('node-zabbix').dataset.tone, 'problem');
      assert.match(elements.get('monitor-status').textContent, /Problem open/);
    }
  }
  assert.equal(elements.get('next').disabled, true);
  assert.equal(elements.get('node-zabbix').dataset.tone, 'healthy');
  elements.get('previous').click();
  assert.equal(app.dataset.step, 'verify');
  elements.get('restart').click();
  assert.equal(app.dataset.step, 'healthy');
  assert.equal(elements.get('reasoning').hidden, true);
});

test('keyboard bounds, rapid navigation and deep links produce deterministic states', () => {
  const { app, key, location } = harness({ hash: '#step=11' });
  assert.equal(app.dataset.step, 'reasoning');
  key('End'); assert.equal(app.dataset.step, 'recovered');
  for (let i = 0; i < 30; i++) key('ArrowRight');
  assert.equal(app.dataset.step, 'recovered');
  key('Home'); assert.equal(app.dataset.step, 'healthy');
  for (let i = 0; i < 30; i++) { key('ArrowRight'); key('ArrowLeft'); }
  assert.equal(app.dataset.step, 'healthy');
  key('r'); assert.equal(location.hash, '#step=1');
  assert.equal(harness({ hash: '#step=999' }).app.dataset.step, 'healthy');
});

test('all 17 technical dialogs use the current source and suspend story keyboard navigation', () => {
  const { app, elements, key } = harness();
  for (const step of model.steps) {
    elements.get('technical').click();
    assert.equal(elements.get('technical-title').textContent, step.title);
    assert.equal(elements.get('technical-code').textContent, step.excerpt);
    assert.equal(elements.get('source-link').href, model.sourceBase + step.source);
    key('End'); assert.equal(app.dataset.step, step.id);
    elements.get('close-technical').click();
    elements.get('next').click();
  }
});

test('reduced motion defaults off, toggling works, and current-step accessibility updates', () => {
  const { app, elements } = harness({ reducedMotion: true });
  assert.equal(app.dataset.motion, 'off');
  assert.equal(elements.get('motion').getAttribute('aria-pressed'), 'false');
  elements.get('motion').click();
  assert.equal(app.dataset.motion, 'on');
  elements.get('next').click();
  assert.equal(elements.get('progress').getAttribute('aria-valuenow'), '2');
  const list = elements.get('workflow-list');
  const buttons = list.children.flatMap(e => e.children).filter(e => e.tagName === 'button');
  assert.equal(buttons.filter(b => b.getAttribute('aria-current') === 'step').length, 1);
  buttons[10].click();
  assert.equal(app.dataset.step, 'reasoning');
  assert.equal(elements.get('reasoning').hidden, false);
});
