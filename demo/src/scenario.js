/* Public simulation only. No infrastructure calls, credentials, or live state. */
(function (root) {
  'use strict';
  const steps = [
  {
    "id": "healthy",
    "phase": "Observe",
    "title": "A healthy place to start.",
    "short": "Server healthy. Monitoring green.",
    "description": "The managed RHEL server has zabbix-agent2 installed and running. Zabbix receives its checks. AAP is ready; the AI runtime is idle.",
    "caption": "Normal checks establish the healthy baseline.",
    "active": [
      "server",
      "zabbix"
    ],
    "flows": [
      "checks"
    ],
    "source": "playbooks/deploy_zabbix_agent.yml",
    "excerpt": "- name: Enable and start zabbix-agent2\n  ansible.builtin.service:\n    name: zabbix-agent2\n    enabled: true\n    state: started",
    "evidence": []
  },
  {
    "id": "failure",
    "phase": "Observe",
    "title": "One package disappears.",
    "short": "The monitoring agent is removed.",
    "description": "The demo failure is removal of zabbix-agent2. The server still runs, but its monitoring agent cannot answer. Zabbix has not detected the failure yet.",
    "caption": "Injected failure: zabbix-agent2 removed. The AI is still idle.",
    "active": [
      "server"
    ],
    "flows": [],
    "source": "README.md",
    "excerpt": "sudo dnf remove -y zabbix-agent2",
    "evidence": []
  },
  {
    "id": "detected",
    "phase": "Observe",
    "title": "Zabbix detects the symptom.",
    "short": "Agent unavailable. Problem raised.",
    "description": "After the configured timeout, Zabbix reports “Zabbix agent is not available.” That is a symptom to investigate, not yet an explanation of the failure.",
    "caption": "Monitoring is red. An alert does not wake the AI directly.",
    "active": [
      "server",
      "zabbix"
    ],
    "flows": [
      "checks"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "## 6. Alerts Are Symptoms\n\nTreat Zabbix alert names as symptoms, not root causes. Always investigate host agent availability and interface status before concluding on root cause. Never act on the alert name alone.",
    "evidence": []
  },
  {
    "id": "event",
    "phase": "Trigger",
    "title": "Monitoring sends an event.",
    "short": "Zabbix → AAP Event Stream.",
    "description": "The Zabbix action sends the problem event to the authenticated AAP Event Stream. Event delivery and automated diagnosis are separate steps.",
    "caption": "The event enters Event-Driven Ansible inside AAP.",
    "active": [
      "zabbix",
      "eda"
    ],
    "flows": [
      "event"
    ],
    "source": "docs/06-eda-zabbix-integration.md",
    "excerpt": "HTTPS POST to AAP Event Stream URL (gateway-managed, authenticated)\n    |\n    v\nEvent Stream forwards to EDA activation via pg_listener",
    "evidence": []
  },
  {
    "id": "matched",
    "phase": "Trigger",
    "title": "EDA matches the event.",
    "short": "A rule selects the investigation job.",
    "description": "Event-Driven Ansible matches the event name against the agent-unavailable rule. EDA belongs to AAP and routes the event to the existing investigation job template.",
    "caption": "EDA matches the symptom; it does not diagnose the root cause.",
    "active": [
      "eda"
    ],
    "flows": [],
    "source": "extensions/eda/rulebooks/zabbix-webhook.yml",
    "excerpt": "condition: event.payload.event_name is search(\"Zabbix agent is not available\", ignorecase=true)\naction:\n  run_job_template:\n    name: \"Run Claude to analyse and fix\"\n    organization: \"Default\"",
    "evidence": []
  },
  {
    "id": "investigation-job",
    "phase": "Trigger",
    "title": "AAP launches the investigation job.",
    "short": "EDA → Automation Controller.",
    "description": "EDA requests “Run Claude to analyse and fix.” Automation Controller starts the job that runs the agent launcher on the agent runtime host.",
    "caption": "An AAP job is the explicit bridge from the event to the AI.",
    "active": [
      "eda",
      "controller"
    ],
    "flows": [
      "eda-job"
    ],
    "source": "extensions/eda/rulebooks/zabbix-webhook.yml",
    "excerpt": "action:\n  run_job_template:\n    name: \"Run Claude to analyse and fix\"\n    organization: \"Default\"",
    "evidence": []
  },
  {
    "id": "agent-awake",
    "phase": "Trigger",
    "title": "The AAP job wakes the AI.",
    "short": "Claude Code CLI starts headlessly.",
    "description": "The launcher invokes Claude Code CLI on its runtime host. The agent can now investigate through its configured MCP interfaces. It has not requested a remediation.",
    "caption": "AAP launches the agent runtime. Investigation comes next.",
    "active": [
      "controller",
      "agent"
    ],
    "flows": [
      "wake"
    ],
    "source": "playbooks/run_claude_analyse_fix.yml",
    "excerpt": "- name: Run Claude Code CLI\n  ansible.builtin.shell: >-\n    claude -p\n    \"There is an alert on Zabbix, root cause analyse the alert and the state\n    of the affected server, and fix it autonomously. Afterwards create an\n    incident report and suggested further steps.\"\n    --model claude-opus-5\n    --dangerously-skip-permissions",
    "evidence": []
  },
  {
    "id": "monitoring-investigation",
    "phase": "Investigate",
    "title": "First, understand the alert.",
    "short": "AI → Zabbix MCP → monitoring.",
    "description": "Through Zabbix MCP, the AI checks alert onset, agent availability, network reachability, and related symptoms. The simulated findings establish when agent monitoring stopped while the server remained reachable.",
    "caption": "Read-only investigation: monitoring evidence returns through Zabbix MCP.",
    "active": [
      "agent",
      "zabbix-mcp",
      "zabbix"
    ],
    "flows": [
      "ai-zabbix",
      "mcp-zabbix"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 1 — Monitoring checks (Zabbix MCP)\n1. Note the alert onset time from Zabbix — this is the reference timestamp for all correlations.\n3. Check network/ICMP reachability in Zabbix.\n6. Correlate all other active problems on this host and related hosts.",
    "evidence": [
      "Alert onset established",
      "Agent unavailable; network reachable"
    ]
  },
  {
    "id": "linux-investigation",
    "phase": "Investigate",
    "title": "Then, inspect the server.",
    "short": "AI → Linux MCP → RHEL.",
    "description": "Through Linux MCP, the AI inspects services, installed packages, logs, and system state. The simulated package check shows zabbix-agent2 is absent; service and package-log timing align with the monitoring failure.",
    "caption": "Read-only diagnostics establish the missing package. No repair runs here.",
    "active": [
      "agent",
      "linux-mcp",
      "server"
    ],
    "flows": [
      "ai-linux",
      "mcp-linux"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 2 — Host checks (linux-mcp)\n2. Check service status (`get_service_status`, `list_services`).\n4. Verify software is installed — always do this when a service is dead. Do NOT trust systemd's `loaded` state; unit files persist after package removal if `daemon-reload` was not run.\n5. Read service logs (`get_service_logs`, `get_journal_logs`). Cross-reference timestamps against the Zabbix alert onset time.",
    "evidence": [
      "zabbix-agent2 absent",
      "Service unavailable; logs align with onset"
    ]
  },
  {
    "id": "aap-investigation",
    "phase": "Investigate",
    "title": "Check the automation history, too.",
    "short": "AI → AAP MCP → Controller.",
    "description": "Through AAP MCP, the AI reviews recent automation activity and job history around the alert onset. In this simulated incident, no relevant AAP job explains the package removal. All three systems have now been investigated.",
    "caption": "Read-only AAP context completes the diagnostic evidence.",
    "active": [
      "agent",
      "aap-mcp",
      "controller"
    ],
    "flows": [
      "ai-aap",
      "mcp-aap"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 3 — AAP context check (AAP MCP)\n1. Check recent AAP job runs — did any job execute close to the alert onset time?\n2. Correlate job completion timestamps against the Zabbix alert onset time.",
    "evidence": [
      "Recent jobs checked against alert onset",
      "No matching automation change in this simulation"
    ]
  },
  {
    "id": "reasoning",
    "phase": "Reason",
    "title": "Three sources. One root cause.",
    "short": "Correlate evidence before choosing a fix.",
    "description": "Monitoring lost the agent, Linux confirms the package is absent, and AAP history provides no competing explanation. The AI correlates these findings: removing zabbix-agent2 caused the monitoring failure.",
    "caption": "Diagnosis: missing zabbix-agent2. The AI reasons; the server is unchanged.",
    "active": [
      "agent"
    ],
    "flows": [],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "## 6. Alerts Are Symptoms\n\nTreat Zabbix alert names as symptoms, not root causes. Always investigate host agent availability and interface status before concluding on root cause. Never act on the alert name alone.",
    "evidence": [
      "Monitoring: agent unavailable",
      "Linux: package absent",
      "AAP: job history reviewed"
    ]
  },
  {
    "id": "discover",
    "phase": "Select",
    "title": "Find the automation that already exists.",
    "short": "AI → AAP MCP → remediation catalog.",
    "description": "The AI queries AAP through MCP for an existing job template that fits the diagnosis. “Deploy Zabbix Agent” already installs, configures, and starts the missing agent. Existing automation gains a new way to be selected.",
    "caption": "The AI discovers a remediation in the existing AAP catalog.",
    "active": [
      "agent",
      "aap-mcp",
      "controller",
      "catalog"
    ],
    "flows": [
      "ai-aap",
      "mcp-aap",
      "catalog-read"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 4 — Remediation (AAP only)\n1. Identify whether an existing AAP job template can fix the root cause.",
    "evidence": [
      "Existing template: Deploy Zabbix Agent",
      "Installs package; configures and starts service"
    ]
  },
  {
    "id": "request",
    "phase": "Select",
    "title": "Ask AAP to run the selected template.",
    "short": "AI → AAP MCP → job-launch request.",
    "description": "The AI selects “Deploy Zabbix Agent” and requests its launch through AAP MCP. AAP handles the job under its configured access and credential settings. The AI sends a job request; AAP will execute the changes.",
    "caption": "Selection becomes an AAP job request. The host is still broken.",
    "active": [
      "agent",
      "aap-mcp",
      "controller",
      "catalog"
    ],
    "flows": [
      "ai-aap-request",
      "mcp-aap-request",
      "catalog-read"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 4 — Remediation (AAP only)\n2. If yes: launch via AAP. Wait for completion.",
    "evidence": [
      "Selected: Deploy Zabbix Agent",
      "Launch requested through AAP MCP"
    ]
  },
  {
    "id": "execute",
    "phase": "Execute",
    "title": "AAP executes the remediation.",
    "short": "Automation Controller → managed RHEL.",
    "description": "AAP runs the existing playbook on the managed server: install zabbix-agent2, configure its monitoring server, and enable and start the service. The state-changing path originates from AAP.",
    "caption": "AAP executes. The AI does not directly modify the server.",
    "active": [
      "controller",
      "catalog",
      "server"
    ],
    "flows": [
      "execute"
    ],
    "source": "playbooks/deploy_zabbix_agent.yml",
    "excerpt": "- name: Install zabbix-agent2\n  ansible.builtin.dnf:\n    name: zabbix-agent2\n    state: present\n\n- name: Enable and start zabbix-agent2\n  ansible.builtin.service:\n    name: zabbix-agent2\n    enabled: true\n    state: started",
    "evidence": [
      "AAP remediation job running",
      "Monitoring has not confirmed recovery"
    ]
  },
  {
    "id": "job-success",
    "phase": "Execute",
    "title": "The job succeeds. Verification is pending.",
    "short": "Package restored ≠ confirmed recovery.",
    "description": "AAP reports a successful remediation job. The package and service are restored, but the monitoring problem remains unresolved until a subsequent Zabbix check confirms recovery. The AI can review job completion through AAP MCP.",
    "caption": "Job successful. Monitoring stays red while verification is pending.",
    "active": [
      "agent",
      "aap-mcp",
      "controller",
      "server"
    ],
    "flows": [
      "ai-aap",
      "mcp-aap"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 4 — Remediation (AAP only)\n2. If yes: launch via AAP. Wait for completion.\n3. Wait up to 80 seconds for Zabbix to reflect the state change.",
    "evidence": [
      "AAP job: successful",
      "Zabbix: waiting for a new check"
    ]
  },
  {
    "id": "verify",
    "phase": "Verify",
    "title": "Now monitoring confirms the recovery.",
    "short": "A new check, then an MCP confirmation.",
    "description": "A subsequent Zabbix check receives fresh agent data and clears the monitoring problem. Through Zabbix MCP and Linux MCP, the AI confirms monitoring recovery and the restored service. Recovery is supported by observed system state.",
    "caption": "Fresh checks confirm recovery. Monitoring can now turn green.",
    "active": [
      "agent",
      "zabbix-mcp",
      "linux-mcp",
      "zabbix",
      "server"
    ],
    "flows": [
      "checks",
      "ai-zabbix",
      "mcp-zabbix",
      "ai-linux",
      "mcp-linux"
    ],
    "source": "AI_Instructions_Guardrails/CLAUDE.md",
    "excerpt": "### Phase 4 — Remediation (AAP only)\n3. Wait up to 80 seconds for Zabbix to reflect the state change.\n5. If problem persists: restart from Phase 1 with new information.",
    "evidence": [
      "Fresh agent checks received; problem cleared",
      "Service running; recovery verified"
    ]
  },
  {
    "id": "recovered",
    "phase": "Verify",
    "title": "AI reasons. AAP executes. Recovery is verified.",
    "short": "AAP is the Trusted Execution Layer.",
    "description": "The RHEL server is healthy and monitoring is green. Agentic AI extended the value of an existing automation catalog: it investigated, diagnosed, and selected the remediation. AAP executed the changes, and monitoring verified the result.",
    "caption": "AAP is the Trusted Execution Layer.",
    "active": [
      "server",
      "zabbix",
      "controller"
    ],
    "flows": [
      "checks"
    ],
    "source": "README.md",
    "excerpt": "Monitoring → EDA → AAP investigation job → Claude Code CLI\n→ MCP investigation → diagnosis → AAP catalog selection\n→ AAP remediation job → monitoring-confirmed recovery",
    "evidence": [
      "AI: investigation and selection",
      "AAP: execution",
      "Monitoring: verified recovery"
    ]
  }
];
  const flows = [
  {
    "id": "checks",
    "kind": "monitor",
    "to": "zabbix",
    "path": "M185 72 V35 H945 V72",
    "from": "server"
  },
  {
    "id": "event",
    "kind": "event",
    "to": "eda",
    "path": "M1060 217 V551 H1000",
    "from": "zabbix"
  },
  {
    "id": "eda-job",
    "kind": "dispatch",
    "to": "controller",
    "path": "M815 551 H740",
    "from": "eda"
  },
  {
    "id": "wake",
    "kind": "dispatch",
    "to": "agent",
    "path": "M535 505 V244",
    "from": "controller"
  },
  {
    "id": "ai-linux",
    "kind": "read",
    "to": "linux-mcp",
    "path": "M430 183 H385 V289",
    "from": "agent"
  },
  {
    "id": "mcp-linux",
    "kind": "read",
    "to": "server",
    "path": "M310 318 H185 V217",
    "from": "linux-mcp"
  },
  {
    "id": "ai-zabbix",
    "kind": "read",
    "to": "zabbix-mcp",
    "path": "M710 183 H770 V289",
    "from": "agent"
  },
  {
    "id": "mcp-zabbix",
    "kind": "read",
    "to": "zabbix",
    "path": "M855 318 H945 V217",
    "from": "zabbix-mcp"
  },
  {
    "id": "ai-aap",
    "kind": "read",
    "to": "aap-mcp",
    "path": "M650 244 V353",
    "from": "agent"
  },
  {
    "id": "mcp-aap",
    "kind": "read",
    "to": "controller",
    "path": "M650 411 V505",
    "from": "aap-mcp"
  },
  {
    "id": "ai-aap-request",
    "kind": "request",
    "to": "aap-mcp",
    "path": "M650 244 V353",
    "from": "agent"
  },
  {
    "id": "mcp-aap-request",
    "kind": "request",
    "to": "controller",
    "path": "M650 411 V505",
    "from": "aap-mcp"
  },
  {
    "id": "catalog-read",
    "kind": "read",
    "to": "catalog",
    "path": "M465 551 H395",
    "from": "controller"
  },
  {
    "id": "execute",
    "kind": "execute",
    "to": "server",
    "path": "M500 623 V632 H70 V255 H125 V217",
    "from": "controller"
  }
];
  function freeze(value) {
    if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
    return value;
  }
  function stateAt(index) {
    if (!Number.isInteger(index) || index < 0 || index >= steps.length) throw new RangeError('Unknown walkthrough step');
    return freeze({
      index, step: steps[index],
      server: index === 0 ? 'healthy' : index < 13 ? 'missing' : index === 13 ? 'repairing' : index < 15 ? 'restored' : 'healthy',
      monitoring: index < 2 || index >= 15 ? 'healthy' : 'problem',
      monitoringPending: index === 1 || index === 13 || index === 14,
      agent: index < 6 ? 'idle' : index === 10 ? 'reasoning' : index >= 16 ? 'complete' : index >= 13 && index <= 14 ? 'waiting' : 'active',
      investigationJob: index < 5 ? 'ready' : index === 5 ? 'queued' : index < 16 ? 'running' : 'complete',
      remediationJob: index < 12 ? 'ready' : index === 12 ? 'requested' : index === 13 ? 'running' : 'successful',
      rootCause: index >= 10,
      evidence: {
        monitoring: index < 7 ? 'Awaiting investigation' : index >= 15 ? 'Fresh checks confirm recovery' : 'Agent unavailable; server reachable',
        linux: index < 8 ? 'Awaiting investigation' : index >= 14 ? 'Package restored; service running' : 'Package absent; service unavailable',
        aap: index < 9 ? 'Awaiting investigation' : index >= 14 ? 'Remediation job successful' : 'Recent activity and job history checked'
      }
    });
  }
  const api = freeze({ steps, flows, stateAt, version: '1.1.2', sourceBase: 'https://github.com/kvegh/aiops-selfhealing-demo/blob/main/' });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AIOpsDemo = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
