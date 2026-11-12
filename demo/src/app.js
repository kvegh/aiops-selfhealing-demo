/* This frontend changes only its local presentation state. */
(() => {
  'use strict';
  const { steps, flows, stateAt, sourceBase } = globalThis.AIOpsDemo;
  const byId = id => document.getElementById(id);
  const setText = (id, value) => { byId(id).textContent = value; };
  const app = document.querySelector('.app');
  const diagram = byId('architecture');
  const dialog = byId('technical-dialog');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const svgNS = 'http://www.w3.org/2000/svg';
  let index = 0;
  let motion = !reducedMotion.matches;
  let motionChosen = false;
  const actorStatus = ['Idle · waiting for an AAP job','Idle · waiting for an AAP job','Idle · waiting for an AAP job','Idle · waiting for an AAP job','Idle · waiting for an AAP job','Idle · waiting for an AAP job','Awake · ready to investigate','Reading monitoring evidence','Reading Linux diagnostics','Reading AAP job history','Correlating three sources','Discovering existing automation','Requesting an AAP job','Waiting for AAP execution','Checking job completion via MCP','Confirming recovery via MCP','Complete · recovery verified'];
  const flowElements = new Map();
  const entries = [];

  flows.forEach(flow => {
    const group = document.createElementNS(svgNS, 'g');
    group.setAttribute('class', `flow flow-${flow.kind}`);
    group.dataset.flow = flow.id;
    group.dataset.from = flow.from;
    group.dataset.to = flow.to;
    // A crisp light casing keeps active routes legible across the slate AAP header.
    const outline = document.createElementNS(svgNS, 'path');
    outline.setAttribute('d', flow.path);
    outline.setAttribute('class', 'flow-outline');
    const line = document.createElementNS(svgNS, 'path');
    line.setAttribute('d', flow.path);
    line.setAttribute('class', 'flow-line');
    line.setAttribute('marker-end', `url(#arrow-${flow.kind})`);
    if (flow.kind === 'read') line.setAttribute('marker-start', 'url(#arrow-read)');
    const signal = document.createElementNS(svgNS, 'path');
    signal.setAttribute('d', flow.path);
    signal.setAttribute('class', 'flow-signal');
    signal.setAttribute('pathLength', '100');
    group.append(outline, line, signal);
    byId('flows').append(group);
    flowElements.set(flow.id, group);
  });

  let lastPhase;
  steps.forEach((step, i) => {
    if (step.phase !== lastPhase) {
      const heading = document.createElement('li');
      heading.className = 'phase-heading';
      heading.textContent = step.phase;
      byId('workflow-list').append(heading);
      lastPhase = step.phase;
    }
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'step-button';
    button.dataset.step = i;
    const number = document.createElement('span');
    number.className = 'step-number';
    number.textContent = String(i + 1).padStart(2, '0');
    const copy = document.createElement('span');
    copy.className = 'step-copy';
    const title = document.createElement('span');
    title.className = 'step-title';
    title.textContent = step.title;
    const short = document.createElement('span');
    short.className = 'step-short';
    short.textContent = step.short;
    copy.append(title, short);
    button.append(number, copy);
    item.append(button);
    byId('workflow-list').append(item);
    button.addEventListener('click', () => render(i));
    entries.push(button);
  });

  function showTechnical() {
    const step = steps[index];
    setText('technical-title', step.title);
    setText('technical-description', step.description);
    setText('technical-code', step.excerpt);
    setText('source-path', step.source);
    byId('source-link').href = sourceBase + step.source;
    dialog.showModal();
  }

  function render(nextIndex, updateHash = true) {
    const state = stateAt(nextIndex);
    index = nextIndex;
    const { step } = state;
    app.dataset.step = step.id;
    app.dataset.phase = step.phase.toLowerCase();
    setText('phase', step.phase);
    setText('step-count', `${String(index + 1).padStart(2, '0')} / ${steps.length}`);
    setText('current-title', step.title);
    setText('current-description', step.description);
    setText('flow-caption', step.caption);
    setText('next-label', steps[index + 1]?.title || 'Recovery verified');
    byId('previous').disabled = index === 0;
    byId('next').disabled = index === steps.length - 1;
    byId('next').querySelector('small').textContent = index === steps.length - 1 ? 'Story complete' : 'Next step';
    byId('progress-fill').style.width = `${(index + 1) / steps.length * 100}%`;
    byId('progress').setAttribute('aria-valuenow', index + 1);
    byId('progress').setAttribute('aria-valuetext', `Step ${index + 1} of ${steps.length}: ${step.title}`);
    diagram.dataset.step = step.id;
    document.querySelectorAll('.component').forEach(node => node.classList.toggle('is-active', step.active.includes(node.id.replace('node-', ''))));
    byId('node-server').dataset.tone = state.server === 'healthy' ? 'healthy' : state.server === 'missing' ? 'problem' : 'pending';
    byId('node-zabbix').dataset.tone = state.monitoring === 'healthy' ? state.monitoringPending ? 'pending' : 'healthy' : 'problem';
    byId('node-agent').dataset.tone = state.agent;
    byId('node-aap-mcp').dataset.tone = step.id === 'request' ? 'request' : '';
    byId('node-catalog').dataset.tone = index >= 12 ? 'selected' : '';
    setText('server-status', {healthy:'Healthy · agent running',missing:'Package absent · agent unavailable',repairing:'Installing and configuring',restored:'Restored · awaiting verification'}[state.server]);
    setText('monitor-status', state.monitoring === 'healthy' ? index === 1 ? 'Last known healthy · check pending' : index >= 15 ? 'Recovered · checks green' : 'Healthy · checks green' : index >= 13 ? 'Problem open · verifying recovery' : 'Problem · agent unavailable');
    setText('monitor-detail', index === 1 ? 'Failure has not been detected yet' : index >= 15 ? 'Fresh checks; problem cleared' : index >= 13 ? 'Waiting for a fresh monitoring check' : index >= 2 ? 'Alert: Zabbix agent is not available' : 'Fresh agent data received');
    setText('agent-status', actorStatus[index]);
    setText('aap-mcp-detail', step.id === 'request' ? 'Request job launch' : 'Read / request a job');
    setText('eda-status', index < 3 ? 'Event Stream ready' : index === 3 ? 'Problem event received' : index === 4 ? 'Rule condition matched' : 'Investigation job dispatched');
    setText('controller-status', index >= 12 ? `Remediation: ${state.remediationJob}` : index >= 5 ? `Investigation: ${state.investigationJob}` : 'Ready for the next job');
    setText('job-status', index >= 12 ? 'Deploy Zabbix Agent' : index >= 5 ? 'Run Claude to analyse and fix' : 'Investigation + remediation jobs');
    setText('catalog-status', index >= 14 ? 'Executed successfully by AAP' : index === 13 ? 'Running on the managed server' : index === 12 ? 'Selected · launch requested' : index === 11 ? 'Found through AAP MCP' : 'Existing automation, ready to run');
    setText('evidence-monitoring', state.evidence.monitoring);
    setText('evidence-linux', state.evidence.linux);
    setText('evidence-aap', state.evidence.aap);
    byId('reasoning').hidden = !state.rootCause;
    byId('reasoning').classList.toggle('is-reasoning', step.id === 'reasoning');
    entries.forEach((button, i) => {
      button.classList.toggle('is-past', i < index);
      if (i === index) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    const scroller = byId('workflow-scroll');
    const active = entries[index];
    const position = active.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop;
    if (position < scroller.scrollTop || position + active.offsetHeight > scroller.scrollTop + scroller.clientHeight) scroller.scrollTop = Math.max(0, position - scroller.clientHeight / 3);
    // Restart finite motion for the current step, including rapid forward/back navigation.
    flowElements.forEach(group => group.classList.remove('is-active'));
    void diagram.getBoundingClientRect();
    step.flows.forEach(id => flowElements.get(id).classList.add('is-active'));
    if (updateHash) history.replaceState(null, '', `#step=${index + 1}`);
  }

  function renderHash() {
    const raw = new URLSearchParams(location.hash.slice(1)).get('step');
    const value = Number(raw);
    render(raw !== null && Number.isInteger(value) && value >= 1 && value <= steps.length ? value - 1 : 0, false);
  }
  function renderMotion() {
    app.dataset.motion = motion ? 'on' : 'off';
    byId('motion').setAttribute('aria-pressed', String(motion));
    setText('motion', motion ? 'Motion on' : 'Motion off');
  }
  byId('next').addEventListener('click', () => { if (index < steps.length - 1) render(index + 1); });
  byId('previous').addEventListener('click', () => { if (index > 0) render(index - 1); });
  byId('restart').addEventListener('click', () => render(0));
  byId('technical').addEventListener('click', showTechnical);
  byId('close-technical').addEventListener('click', () => dialog.close());
  byId('motion').addEventListener('click', () => { motion = !motion; motionChosen = true; renderMotion(); });
  reducedMotion.addEventListener('change', () => { if (!motionChosen) { motion = !reducedMotion.matches; renderMotion(); } });
  window.addEventListener('hashchange', renderHash);
  document.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || dialog.open || event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
    const actions = {ArrowRight: () => render(Math.min(index + 1, steps.length - 1)), ArrowLeft: () => render(Math.max(index - 1, 0)), Home: () => render(0), End: () => render(steps.length - 1), r: () => render(0), R: () => render(0)};
    if (actions[event.key]) { event.preventDefault(); actions[event.key](); }
  });
  renderMotion();
  renderHash();
})();
