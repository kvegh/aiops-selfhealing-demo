# AIOps self-healing demo

AI-driven incident remediation for enterprise infrastructure — with the blast radius bounded by architecture, not by prompting.

## What this is

A reproducible demo in which infrastructure incidents are detected, diagnosed, and remediated automatically — including incidents nobody wrote a runbook for. An AI agent investigates the unknown cases and resolves them, yet at no point holds the ability to change systems directly: every change, without exception, runs through the organization's governed automation platform.

## The core idea

An incident is resolved at the lowest capable level. Known issues never wake the AI; the AI never acts outside approved automation; humans are woken with an analysis, not an alert.

```mermaid
%%{init: {'themeVariables': {'fontSize': '18px'}, 'flowchart': {'nodeSpacing': 40, 'rankSpacing': 60}}}%%
flowchart TD
    INC([Incident detected]) --> KNOWN{Known issue?}
    KNOWN -->|yes| EDA[Event-driven automation<br>executes documented fix]
    EDA --> CLOSED([Issue closed])
    KNOWN -->|no| AI[AI agent woken:<br>analyze & diagnose]
    AI -->|approved fix exists| FIX[Fix executed exclusively through<br>approved automation]
    FIX --> CLOSED
    AI -->|no current fix| HUMAN[Human Ops woken<br>with full analysis]
    AI -.->|no current fix,<br>defined conditions met| CREATE[Agent creates automation content,<br>reviewed & rolled out]
    CREATE -.-> FIX
    ITSM[(ITSM incident)]
    EDA ---|update / close| ITSM
    FIX ---|update / close| ITSM
    HUMAN ---|escalate| ITSM

    classDef default fill:none,stroke:#4a7ebb,stroke-width:2px;
    classDef terminal fill:none,stroke:#5f8f5f,stroke-width:2px;
    classDef human fill:none,stroke:#b0763d,stroke-width:2px;
    classDef experimental fill:none,stroke:#9b6bb3,stroke-width:2px,stroke-dasharray:6 4;
    class INC,CLOSED terminal;
    class HUMAN human;
    class CREATE experimental;
```

Solid borders are the working demo. The dashed purple branch is **experimental** — the agent authoring new automation content is a research direction, not a shipped capability.

## The four response levels

Every incident is handled at the lowest level capable of resolving it. Each level up grants the responding system more autonomy — and pays for it with more scrutiny. Where an incident lands is not a runtime decision made on a whim; it is defined by policy and enforced by architecture.

**Level 0 — Known issue, known fix.**
The incident matches a documented pattern in the knowledge base. A predefined remediation template executes deterministically — no intelligence involved, none needed. This is the operational runbook, executed by the automation platform instead of a person: identical response, every time, fully audited. If the fix does not clear the issue, the re-fired event escalates automatically to Level 1.

**Level 1 — Unknown issue, known remediations.**
No documented pattern matches, or the known fix did not clear the issue. The AI agent is woken to investigate: it examines the affected systems read-only, correlates monitoring data with system state, and determines the cause — then resolves it strictly by selecting from the pre-approved remediation catalog. The agent reasons freely, but acts only within the sanctioned repertoire. Diagnosis is creative; execution never is.

**Level 2 — Unknown issue, no fitting remediation.** *(experimental)*
The catalog holds no answer. The agent drafts a new remediation and submits it as a proposal — it never executes its own work. An independent second agent instance reviews the proposal for sanity and policy compliance before it may enter the catalog, mirroring the author/reviewer separation of established code review practice. Whether machine review is sufficient here, or whether this level always requires a human gate, is an open question this project deliberately leaves open.

**Level 3 — Human escalation.**
Judgment is required beyond what any automation should exercise. The agent compiles the complete diagnostic picture — findings, attempted remediations, ruled-out causes — and wakes a human, who starts at the analysis rather than at a raw alert.

> **Management summary.** The bulk of incidents resolve at Level 0 — machine-speed, audit-grade, with no one paged at 3 a.m. The AI agent absorbs the long tail of unknowns at Level 1, working exclusively through the automation platform the organization already owns and governs — existing investment, extended rather than replaced. Escalations that do reach engineers arrive pre-analyzed, cutting time-to-resolution where expert time is scarcest. Autonomy grows only where control grows with it: every action, at every level, runs through the same governed, auditable execution path.

## Component roles

These are the choices for this demo. Each role can be filled by other tools — the architecture depends on the roles, not the products.

| Role | This demo | Notes |
|------|-----------|-------|
| Monitoring & event source | Zabbix | Any monitoring system capable of forwarding events |
| Automation & orchestration — the Trusted Execution Layer | Ansible Automation Platform (AAP) incl. Event-Driven Ansible | Sole component that changes systems |
| Managed test server (monitored & remediated) | RHEL 9 | Stand-in for any managed fleet |
| Agent runtime server — tools, runtimes, admin (TRA) | RHEL 9 | Hosts the AI agent and its integration layer |
| AI agent | Claude Code (CLI, headless) | Any agentic LLM runtime with policy enforcement |

## Technical architecture

```mermaid
%%{init: {'themeVariables': {'fontSize': '18px'}, 'flowchart': {'nodeSpacing': 45, 'rankSpacing': 70}}}%%
flowchart LR
    ZBX[Monitoring<br>Zabbix] -->|alert| EDA[Event routing<br>Event-Driven Ansible]
    EDA -->|known issue:<br>run template| AAP
    EDA -->|unknown issue:<br>trigger agent| CC

    subgraph TRA[AI agent — TRA server]
        CC[Claude Code CLI<br>headless]
        MEM[(Incident memory<br>MCP)]
        CC <--> MEM
    end

    CC -->|read-only diagnostics<br>via linux-mcp| TGT[Managed server<br>RHEL 9]
    CC -->|request sanctioned job<br>via AAP MCP| AAP

    subgraph TEL[Trusted Execution Layer]
        AAP[AAP Controller<br>remediation catalog]
    end

    AAP -->|remediation via SSH| TGT
    AAP -->|create / update / close| ITSM[(ITSM<br>incident API)]
    TGT -.->|agent data| ZBX

    classDef default fill:none,stroke:#4a7ebb,stroke-width:2px;
    classDef tel fill:none,stroke:#5f8f5f,stroke-width:3px;
    classDef store fill:none,stroke:#888888,stroke-width:2px;
    class AAP tel;
    class MEM,ITSM store;
    style TRA fill:none,stroke:#888888,stroke-width:1px,stroke-dasharray:3 3;
    style TEL fill:none,stroke:#5f8f5f,stroke-width:1px,stroke-dasharray:3 3;
```

The critical property is visible in the diagram: **every arrow that changes state — on the managed server and in the ITSM system — originates from the Trusted Execution Layer.** The AI agent has no direct write path anywhere.

## Guiding principles

- **The automation platform is strictly the only component that changes configurations or executes jobs.** It is the **Trusted Execution Layer**. LLMs are exceptionally creative — and exactly for that reason not reliable enough to follow operational policy unconditionally. Creativity belongs in diagnosis, never in execution.
- **The AI agent changes nothing.** It analyses, correlates, summarizes — and requests fixes through the Trusted Execution Layer.
- **All agent communication runs through defined integration interfaces (MCP)** — to monitoring, to the managed server, to the automation platform. Where no interface exists, the automation platform is triggered to gather the information.
- **Read-only wherever possible.** The agent's interfaces to the managed server and to monitoring are read-only by construction, not by convention.
- **Monitoring may trigger automation jobs directly** when an issue is well known and documented. Otherwise it triggers the AI agent to analyse the situation.
- **The agent operates under policy enforcement** that limits creative side activities outside operational policy — enforced in code, not requested in prompts.

> **Management summary.** Control is not a promise made by the AI — it is a property of the architecture. The single governed execution path preserves every existing approval, audit, and compliance mechanism the organization already relies on. Adopting AI-driven operations this way carries no new class of privileged actor: the platform you already trust remains the only thing touching your systems.

## Demo scenarios

- **Stage 1** — TBD
- **Stage 2** — TBD

## Repository layout

```
docs/            architecture, design decisions, documented failure modes
docs/build/      sequential reimplementation guide (start at 00-starting-setup.md)
playbooks/       AAP project content used by the remediation templates
rulebooks/       EDA rulebooks (level routing)
config/          sanitized reference configuration (AAP installer inventory, MCP configs, agent settings)
```

## Status

Working demo; documentation in progress. Failure modes and design decisions are documented deliberately — real behavior over polished success.
