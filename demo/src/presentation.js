/* A separate projector drawing reuses the existing story and renderer.
 * Justification: ../../docs/12-interactive-recovery-walkthrough.md#presentation-mode
 * Fixed presentation markup only; no network access, incident state, or tool calls.
 */
(() => {
  'use strict';

  // Alternate coordinates for the same flow IDs, directions, and MCP boundaries.
  const flowPaths = Object.freeze({
    checks: 'M260 30 V10 H1340 V30',
    event: 'M1540 140 H1570 V542 H1490',
    'eda-job': 'M1090 520 H1025',
    wake: 'M970 480 V350 H1055 V180 H1000',
    'ai-linux': 'M600 115 H500 V287 H430',
    'mcp-linux': 'M300 250 V230 H260 V210',
    'ai-zabbix': 'M1000 115 H1100 V287 H1170',
    'mcp-zabbix': 'M1300 250 V230 H1340 V210',
    'ai-aap': 'M800 210 V250',
    'mcp-aap': 'M800 325 V465 H810 V480',
    'ai-aap-request': 'M800 210 V250',
    'mcp-aap-request': 'M800 325 V465 H810 V480',
    'catalog-read': 'M595 520 H530',
    execute: 'M595 550 H565 V465 H85 V230 H140 V210'
  });

  const markup = `
<svg id="presentation-architecture" class="presentation-architecture" viewBox="0 0 1600 660" preserveAspectRatio="xMidYMid meet" role="img" aria-labelledby="presentation-diagram-title presentation-diagram-description">
  <title id="presentation-diagram-title">AIOps recovery: AI reasons, AAP executes</title>
  <desc id="presentation-diagram-description">A production server is monitored by Zabbix. An event reaches Event-Driven Ansible inside Ansible Automation Platform. A Controller job starts agentic AI. Investigation and job requests pass through Linux, Zabbix, and AAP MCP interfaces. Only AAP executes the remediation. A later monitoring check confirms recovery.</desc>
  <defs>
    <marker id="presentation-arrow-read" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="15" markerHeight="15" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1 1 9 5 1 9" fill="none" stroke="#0051a8" stroke-width="2"/></marker>
    <marker id="presentation-arrow-request" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 10 5 0 10Z" fill="#53389e"/></marker>
    <marker id="presentation-arrow-event" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 10 5 0 10Z" fill="#334d68"/></marker>
    <marker id="presentation-arrow-dispatch" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 10 5 0 10Z" fill="#334d68"/></marker>
    <marker id="presentation-arrow-execute" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="18" markerHeight="18" markerUnits="userSpaceOnUse" orient="auto"><path d="M0 0 10 5 0 10Z" fill="#006b73"/></marker>
    <marker id="presentation-arrow-monitor" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="15" markerHeight="15" markerUnits="userSpaceOnUse" orient="auto"><path d="M1 1 9 5 1 9" fill="none" stroke="#186440" stroke-width="2"/></marker>
  </defs>

  <g class="platform-base">
    <rect class="platform-frame" x="60" y="385" width="1480" height="260" rx="7" fill="#e7eff7"/>
    <path class="platform-header" d="M67 385 H1533 Q1540 385 1540 392 V465 H60 V392 Q60 385 67 385Z"/>
    <path d="M67 385 H1533" stroke="#ee0000" stroke-width="3"/>
    <text x="90" y="437" class="platform-name" textLength="650" lengthAdjust="spacingAndGlyphs">Ansible Automation Platform</text>
    <text x="1510" y="435" text-anchor="end" class="platform-label">TRUSTED EXECUTION LAYER</text>
  </g>
  <g id="presentation-flows" aria-hidden="true"></g>

  <g id="presentation-node-server" data-node="server" class="component server-node" data-tone="healthy">
    <rect class="node-surface" x="60" y="30" width="400" height="180" rx="9"/>
    <text x="88" y="75" class="node-title">PROD SERVER</text>
    <text x="88" y="108" class="node-product">Red Hat Enterprise Linux</text>
    <text id="presentation-server-status" x="88" y="149" class="node-status" data-wrap-width="344" data-line-height="30">Healthy · agent running</text>
  </g>

  <g id="presentation-node-zabbix" data-node="zabbix" class="component monitoring-node" data-tone="healthy">
    <rect class="node-surface" x="1140" y="30" width="400" height="180" rx="9"/>
    <text x="1168" y="75" class="node-title">MONITORING</text>
    <text x="1168" y="108" class="node-product">Zabbix in this case</text>
    <text id="presentation-monitor-status" x="1168" y="149" class="node-status" data-wrap-width="344" data-line-height="30">Healthy · checks green</text>
    <text id="presentation-monitor-detail" x="1168" y="199" class="projection-fineprint">Fresh agent data received</text>
  </g>

  <g id="presentation-node-agent" data-node="agent" class="component agent-node" data-tone="idle">
    <rect class="agent-halo" x="590" y="20" width="420" height="200" rx="13"/>
    <rect class="node-surface" x="600" y="30" width="400" height="180" rx="9"/>
    <g class="agent-constellation" transform="translate(947 77)">
      <path d="M0 -24 24 -10 23 14 0 28 -24 14 -24 -10Z M0 -24 V28 M-24 -10 23 14 M24 -10 -24 14 M0 -24 23 14 M0 -24 -24 14 M-24 -10 0 28 M24 -10 0 28"/>
      <circle class="agent-core" cx="0" cy="0" r="8"/>
      <circle cx="0" cy="-24" r="3"/><circle cx="24" cy="-10" r="3"/><circle cx="23" cy="14" r="3"/>
      <circle cx="0" cy="28" r="3"/><circle cx="-24" cy="14" r="3"/><circle cx="-24" cy="-10" r="3"/>
    </g>
    <text x="628" y="75" class="node-title agent-role">AGENTIC AI</text>
    <text x="628" y="108" class="node-product">Claude in this case</text>
    <rect class="status-highlight" x="616" y="123" width="368" height="72" rx="6" aria-hidden="true"/>
    <text id="presentation-agent-status" x="628" y="149" class="agent-status" data-wrap-width="344" data-line-height="30">Idle · waiting for an AAP job</text>
  </g>

  <g id="presentation-node-linux-mcp" data-node="linux-mcp" class="component mcp-node">
    <rect class="node-surface" x="170" y="250" width="260" height="75" rx="6"/>
    <text x="300" y="281" text-anchor="middle" class="mcp-title">Linux MCP</text>
    <text x="300" y="310" text-anchor="middle" class="mcp-detail">Read diagnostics</text>
  </g>
  <g id="presentation-node-aap-mcp" data-node="aap-mcp" class="component mcp-node">
    <rect class="node-surface" x="670" y="250" width="260" height="75" rx="6"/>
    <text x="800" y="281" text-anchor="middle" class="mcp-title">AAP MCP</text>
    <text id="presentation-aap-mcp-detail" x="800" y="310" text-anchor="middle" class="mcp-detail">Read / request a job</text>
  </g>
  <g id="presentation-node-zabbix-mcp" data-node="zabbix-mcp" class="component mcp-node">
    <rect class="node-surface" x="1170" y="250" width="260" height="75" rx="6"/>
    <text x="1300" y="281" text-anchor="middle" class="mcp-title">Zabbix MCP</text>
    <text x="1300" y="310" text-anchor="middle" class="mcp-detail">Read monitoring</text>
  </g>

  <g id="presentation-node-catalog" data-node="catalog" class="component platform-node catalog-node">
    <rect class="node-surface" x="110" y="480" width="420" height="125" rx="5"/>
    <text x="138" y="509" class="platform-node-title">Remediation catalog</text>
    <rect class="template-surface" x="130" y="517" width="380" height="33" rx="4"/>
    <text x="147" y="541" class="template-name">Deploy Zabbix Agent</text>
    <text id="presentation-catalog-status" x="138" y="569" class="platform-status" data-wrap-width="364" data-line-height="25">Existing automation, ready to run</text>
  </g>
  <g id="presentation-node-controller" data-node="controller" class="component platform-node controller-node">
    <rect class="node-surface" x="595" y="480" width="430" height="125" rx="5"/>
    <text x="623" y="518" class="platform-node-title">Automation Controller</text>
    <text id="presentation-controller-status" x="623" y="554" class="platform-status" data-wrap-width="374" data-line-height="30">Ready for the next job</text>
    <text id="presentation-job-status" x="623" y="599" class="projection-fineprint">Investigation + remediation jobs</text>
  </g>
  <g id="presentation-node-eda" data-node="eda" class="component platform-node eda-node">
    <rect class="node-surface" x="1090" y="480" width="400" height="125" rx="5"/>
    <text x="1118" y="518" class="platform-node-title">Event-Driven Ansible</text>
    <rect class="status-highlight" x="1106" y="530" width="368" height="65" rx="6" aria-hidden="true"/>
    <text id="presentation-eda-status" x="1118" y="554" class="platform-status" data-wrap-width="344" data-line-height="30">Event Stream ready</text>
  </g>
  <g class="platform-capabilities" aria-hidden="true">
    <text x="110" y="633" class="platform-capability">RBAC</text>
    <text x="455" y="633" class="platform-capability">Credential handling</text>
    <text x="870" y="633" class="platform-capability">Job logging</text>
    <text x="1190" y="633" class="platform-capability">Activity auditing</text>
  </g>
</svg>`;

  let mounted;
  function mount() {
    if (mounted) return mounted;
    const stage = document.getElementById('presentation-stage');
    if (!stage) throw new Error('The presentation drawing needs its stage element.');
    // The markup is a fixed local asset; no external strings are interpolated.
    stage.innerHTML = markup;
    mounted = Object.freeze({
      diagram: document.getElementById('presentation-architecture'),
      flows: document.getElementById('presentation-flows')
    });
    return mounted;
  }

  globalThis.AIOpsPresentation = Object.freeze({ mount, flowPaths });
})();
