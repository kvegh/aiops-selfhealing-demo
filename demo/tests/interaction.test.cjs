// Minimal DOM harness for actual app handlers; this does not verify browser layout.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const model = require('../src/scenario.js');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const appCode = fs.readFileSync(path.join(__dirname, '../src/app.js'), 'utf8');
const presentationCode = fs.readFileSync(path.join(__dirname, '../src/presentation.js'), 'utf8');

function harness({ reducedMotion = false, hash = '' } = {}) {
  const elements = new Map();
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag; this.children = []; this.attributes = {}; this.dataset = {}; this.style = {}; this.listeners = {};
      this._text = ''; this.hidden = false; this.scrollTop = 0; this.clientHeight = 600; this.offsetHeight = 30;
      this.classList = {
        values: new Set(),
        add: (...names) => names.forEach(name => this.classList.values.add(name)),
        remove: (...names) => names.forEach(name => this.classList.values.delete(name)),
        contains: name => this.classList.values.has(name),
        toggle: (name, enabled = !this.classList.values.has(name)) => enabled ? this.classList.values.add(name) : this.classList.values.delete(name)
      };
    }
    setAttribute(name, value) {
      const string = String(value);
      this.attributes[name] = string;
      if (name === 'id') { this.id = string; elements.set(string, this); }
      if (name === 'class') this.classList.values = new Set(string.split(/\s+/).filter(Boolean));
      if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = string;
      if (name === 'hidden' || name === 'disabled') this[name] = true;
    }
    getAttribute(name) { return this.attributes[name] ?? null; }
    removeAttribute(name) { delete this.attributes[name]; }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
    set innerHTML(markup) { this._text = ''; this.children = []; readMarkup(markup, this); }
    append(...children) { children.forEach(child => { child.parentElement = this; this.children.push(child); }); }
    addEventListener(name, handler) { (this.listeners[name] ||= []).push(handler); }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    querySelectorAll(selector) {
      const matches = element => {
        if (selector.startsWith('.')) return element.classList.contains(selector.slice(1));
        if (selector.startsWith('#')) return element.id === selector.slice(1);
        if (/^\[[\w-]+\]$/.test(selector)) return element.getAttribute(selector.slice(1, -1)) !== null;
        return element.tagName === selector;
      };
      return this.children.flatMap(child => [...(matches(child) ? [child] : []), ...child.querySelectorAll(selector)]);
    }
    closest() { return null; }
    getBoundingClientRect() { return { top: 0 }; }
    // Synthetic measurement exercises wrapping control flow, never real glyph fit.
    getComputedTextLength() { return this.textContent.length * 14; }
    showModal() { this.open = true; }
    close() { this.open = false; }
    click() { if (!this.disabled) for (const handler of this.listeners.click || []) handler({ target: this }); }
  }
  // Read only the trusted local HTML/SVG fixture, not arbitrary browser markup.
  function readMarkup(markup, root) {
    const stack = [root];
    const voidTags = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
    const decode = value => value.replace(/&(amp|lt|gt|quot|#39|nbsp);/g, (_, name) => ({ amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", nbsp: ' ' })[name]);
    for (const token of markup.matchAll(/<!--[\s\S]*?-->|<[^>]+>|[^<]+/g)) {
      const value = token[0];
      if (value.startsWith('<!--') || value.startsWith('<!')) continue;
      if (value.startsWith('</')) { if (stack.length > 1) stack.pop(); continue; }
      if (!value.startsWith('<')) { stack.at(-1)._text += decode(value); continue; }
      const [, tag, source] = value.match(/^<([\w:-]+)([\s\S]*?)\/?>(?:$)/) || [];
      if (!tag) continue;
      const element = new Element(tag);
      for (const attribute of source.matchAll(/([\w:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) {
        element.setAttribute(attribute[1], decode(attribute[2] ?? attribute[3] ?? attribute[4] ?? ''));
      }
      stack.at(-1).append(element);
      if (!value.endsWith('/>') && !voidTags.has(tag)) stack.push(element);
    }
  }
  const document = new Element('document');
  readMarkup(html, document);
  document.getElementById = id => elements.get(id) || null;
  document.createElement = tag => new Element(tag);
  document.createElementNS = (_, tag) => new Element(tag);
  const app = document.querySelector('.app');
  const window = new Element();
  const location = { hash };
  const media = new Element(); media.matches = reducedMotion;
  const context = { document, window, location, history: { replaceState: (_, __, value) => { location.hash = value; } }, matchMedia: () => media, URLSearchParams, AIOpsDemo: model };
  vm.createContext(context);
  vm.runInContext(presentationCode, context);
  vm.runInContext(appCode, context);
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


const mirroredLabels = ['server-status', 'monitor-status', 'monitor-detail', 'agent-status', 'aap-mcp-detail', 'eda-status', 'controller-status', 'job-status', 'catalog-status'];
const componentNames = ['server', 'zabbix', 'agent', 'linux-mcp', 'zabbix-mcp', 'aap-mcp', 'controller', 'catalog', 'eda'];

function assertViewVisibility(elements, presentation) {
  assert.equal(elements.get('presentation-mode').getAttribute('aria-pressed'), String(presentation));
  assert.equal(elements.get('presentation-mode').textContent, presentation ? 'Exit presentation mode' : 'Enable presentation mode');
  assert.equal(elements.get('standard-stage').hidden, presentation);
  assert.equal(elements.get('presentation-stage').hidden, !presentation);
  assert.equal(elements.get('workflow-panel').hidden, presentation);
}

test('presentation mode switches instantly at a deep-linked reasoning step without changing story or motion state', () => {
  const { app, elements, location } = harness({ reducedMotion: true, hash: '#step=11' });
  const observedIds = ['current-title', 'current-description', 'flow-caption', 'next-label', 'evidence-monitoring', 'evidence-linux', 'evidence-aap'];
  const before = observedIds.map(id => elements.get(id).textContent);
  assert.equal(app.dataset.view, 'standard');
  assertViewVisibility(elements, false);
  for (const presentation of [true, false, true, false]) {
    elements.get('presentation-mode').click();
    assert.equal(app.dataset.view, presentation ? 'presentation' : 'standard');
    assertViewVisibility(elements, presentation);
    assert.equal(app.dataset.step, 'reasoning');
    assert.equal(location.hash, '#step=11');
    assert.equal(app.dataset.motion, 'off');
    assert.deepEqual(observedIds.map(id => elements.get(id).textContent), before);
    for (const id of mirroredLabels) assert.equal(elements.get(`presentation-${id}`).textContent, elements.get(id).textContent, id);
    if (presentation) assert.ok(elements.get('presentation-monitor-status').children.length > 1, 'synthetic measurement must exercise multi-line wrapping');
  }
});

test('both designs retain identical statuses, active components and MCP/AAP flows through every recovery step', () => {
  const { app, elements } = harness();
  for (const [index, step] of model.steps.entries()) {
    if (index) elements.get('next').click();
    elements.get('presentation-mode').click();
    assert.equal(app.dataset.step, step.id);
    assert.equal(app.dataset.view, index % 2 === 0 ? 'presentation' : 'standard');
    for (const id of mirroredLabels) assert.equal(elements.get(`presentation-${id}`).textContent, elements.get(id).textContent, `${step.id}: ${id}`);
    for (const name of componentNames) {
      const standard = elements.get(`node-${name}`);
      const presentation = elements.get(`presentation-node-${name}`);
      assert.equal(standard.classList.contains('is-active'), step.active.includes(name), `${step.id}: ${name}`);
      assert.equal(presentation.classList.contains('is-active'), standard.classList.contains('is-active'), `${step.id}: presentation ${name}`);
      if (['server', 'zabbix', 'agent', 'aap-mcp', 'catalog'].includes(name)) {
        assert.equal(presentation.dataset.tone, standard.dataset.tone, `${step.id}: ${name} tone`);
      }
    }
    for (const container of ['flows', 'presentation-flows']) {
      const groups = elements.get(container).children;
      assert.equal(groups.length, model.flows.length);
      assert.deepEqual(groups.filter(group => group.classList.contains('is-active')).map(group => group.dataset.flow).sort(), [...step.flows].sort(), `${step.id}: ${container}`);
      for (const group of groups) {
        const flow = model.flows.find(flow => flow.id === group.dataset.flow);
        assert.equal(group.dataset.from, flow.from);
        assert.equal(group.dataset.to, flow.to);
      }
    }
    if (step.id === 'job-success') {
      assert.equal(elements.get('presentation-node-zabbix').dataset.tone, 'problem');
      assert.match(elements.get('presentation-monitor-status').textContent, /Problem open/);
    }
    if (step.id === 'verify' || step.id === 'recovered') assert.equal(elements.get('presentation-node-zabbix').dataset.tone, 'healthy');
  }
});

test('presentation navigation, restart and technical detail retain the chosen view and explicit motion choice', () => {
  const { app, elements, key, location } = harness({ hash: '#step=13' });
  elements.get('motion').click();
  assert.equal(app.dataset.motion, 'off');
  elements.get('presentation-mode').click();
  key('End');
  assert.equal(app.dataset.step, 'recovered');
  elements.get('restart').click();
  assert.equal(app.dataset.step, 'healthy');
  assert.equal(location.hash, '#step=1');
  assert.equal(app.dataset.view, 'presentation');
  assert.equal(app.dataset.motion, 'off');
  assertViewVisibility(elements, true);
  elements.get('technical').click();
  assert.equal(elements.get('technical-title').textContent, model.steps[0].title);
  assert.equal(elements.get('technical-description').textContent, model.steps[0].description);
  assert.equal(elements.get('source-link').href, model.sourceBase + model.steps[0].source);
  key('End');
  assert.equal(app.dataset.step, 'healthy');
  elements.get('close-technical').click();
  key('ArrowRight');
  assert.equal(app.dataset.step, 'failure');
  elements.get('presentation-mode').click();
  assert.equal(app.dataset.view, 'standard');
  assert.equal(app.dataset.step, 'failure');
  assert.equal(app.dataset.motion, 'off');
  assertViewVisibility(elements, false);
});
