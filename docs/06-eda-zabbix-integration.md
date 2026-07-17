# 06 -- EDA / Zabbix integration

This section connects Zabbix to Event-Driven Ansible so that alerts
automatically trigger the Claude agent via AAP. Zabbix ships a native
**Event-Driven Ansible** media type -- import it, point it at EDA, and
configure an action. No custom scripts or JavaScript required.

## Environment

- Zabbix 6.4+ with admin access (from [00-starting-setup](00-starting-setup.md))
- AAP 2.7 with EDA controller (from [00-starting-setup](00-starting-setup.md))
- EDA rulebook and playbook committed to a project repo synced in AAP

## Components

| Component | Purpose |
|-----------|---------|
| Zabbix media type | Ships with Zabbix -- sends alert payloads to EDA over HTTP |
| Zabbix trigger action | Fires the media type when a problem event occurs |
| EDA rulebook | Receives the webhook, matches alert conditions, launches the AAP job template |
| AAP job template | Runs the playbook that invokes Claude Code CLI |

## 1. Import the Event-Driven Ansible media type in Zabbix

Zabbix ships pre-built integration templates. The EDA media type is
included out of the box.

1. Navigate to **Alerts --> Media types**.
2. Click **Import** (top right).
3. Select the `media_event_driven_ansible.yaml` file from the
   [Zabbix integrations page](https://www.zabbix.com/integrations/ansible#event_driven_ansible)
   or from the Zabbix installation directory
   (`/usr/share/zabbix/zabbix_export/media_types/` on the appliance).
4. Import it.

The media type appears as **Event-Driven Ansible** in the list. Open
it to review the parameters -- the key one is `endpoint_url`, which
you will configure per-user in the next step.

## 2. Create a Zabbix user for EDA notifications

Create a dedicated user (or use the existing admin) and assign the
EDA media type.

1. Navigate to **Users --> Users --> Create user** (or edit an
   existing user).
2. Go to the **Media** tab, click **Add**.
3. Set the fields:

| Field | Value |
|-------|-------|
| Type | Event-Driven Ansible |
| Send to | `http://EDA_HOST:5000/endpoint` |
| Enabled | checked |

Replace `EDA_HOST` with the address of the AAP EDA controller or the
host running `ansible-rulebook`. The port must match the rulebook's
webhook source port.

4. Ensure the user has at least read permissions on the host groups
   you want to trigger on.

> **One rulebook, one port:** Each `ansible.eda.webhook` source
> listens on a unique port. If you run multiple rulebooks, each needs
> a separate media entry with its own port.

## 3. Create a trigger action

This tells Zabbix to send events to EDA when problems occur.

1. Navigate to **Alerts --> Actions --> Trigger actions**.
2. Click **Create action**.

### Action tab

| Field | Value |
|-------|-------|
| Name | `EDA self-healing` |
| Conditions | Add conditions to scope which alerts trigger EDA (e.g. host group, severity >= Warning) |
| Enabled | checked |

### Operations tab

1. Click **Add** under Operations.
2. Set:

| Field | Value |
|-------|-------|
| Send to users | Select the user from step 2 |
| Send only to | Event-Driven Ansible |

3. Save the action.

From this point, any Zabbix problem event matching the action
conditions will POST the alert payload to the EDA webhook endpoint.

## 4. EDA rulebook

The rulebook listens for incoming webhooks and launches an AAP job
template when a matching alert arrives.

File: `eda/zabbix-webhook.yml`

```yaml
---
- name: Receive Zabbix alerts via webhook
  hosts: all
  sources:
    - ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
  rules:
    - name: Zabbix agent down - invoke Claude
      condition: event.payload.alert_name == "Linux: Zabbix agent is not available"
      action:
        run_job_template:
          name: "Run Claude to analyse and fix"
          organization: "Default"
```

The `condition` field matches on the alert name passed by the Zabbix
media type. Adjust the condition to match the alerts you want to
handle. The `run_job_template` action launches the AAP job template by
name.

> **Condition field names:** The exact field names in
> `event.payload.*` depend on the parameters defined in the Zabbix
> media type. Open the imported media type to see which macros are
> passed (e.g. `alert_name`, `host_name`, `trigger_severity`).

## 5. AAP job template and playbook

The job template **Run Claude to analyse and fix** must exist in AAP
and point to the playbook that invokes Claude Code CLI.

File: `playbooks/run_claude_analyse_fix.yml`

```yaml
---
- name: Run Claude to analyse and fix Zabbix alert
  hosts: all
  gather_facts: false

  tasks:
    - name: Run Claude Code CLI
      ansible.builtin.shell: >-
        claude -p
        "There is an alert on Zabbix, root cause analyse the alert and the state
        of the affected server, and fix it autonomously. Afterwards create an
        incident report and suggested further steps."
        --dangerously-skip-permissions
      args:
        chdir: /home/aaptra/claude-wd
      become: true
      become_user: aaptra
      register: claude_output

    - name: Display incident report
      ansible.builtin.debug:
        var: claude_output.stdout_lines
```

The job template in AAP should:

- Point to the project containing this playbook
- Target the TRA VM (where Claude Code CLI is installed)
- Use credentials that allow `become_user: aaptra` on the TRA VM

## 6. End-to-end flow

```
Zabbix trigger fires
    |
    v
Zabbix action matches --> sends via EDA media type
    |
    v
HTTP POST to EDA webhook (port 5000)
    |
    v
EDA rulebook matches condition --> run_job_template
    |
    v
AAP launches "Run Claude to analyse and fix"
    |
    v
Playbook runs on TRA VM as aaptra
    |
    v
Claude Code CLI diagnoses via MCP servers, remediates via AAP
```

## 7. Test the integration

### Manual webhook test

Simulate a Zabbix alert to verify the EDA path without waiting for a
real problem:

```bash
curl -X POST http://EDA_HOST:5000/endpoint \
  -H "Content-Type: application/json" \
  -d '{"alert_name": "Linux: Zabbix agent is not available", "host_name": "testserver1"}'
```

Check the EDA controller (or `ansible-rulebook` output) for the
matched rule, and the AAP controller for the launched job.

### Live test

1. Stop the Zabbix agent on the target server (or simulate a failure
   the monitoring template detects).
2. Wait for Zabbix to fire the trigger.
3. Observe the action log in **Alerts --> Actions --> Action log**.
4. Confirm the EDA rulebook matched and launched the job template.
5. Confirm Claude diagnosed and remediated the issue.
6. Confirm the Zabbix problem clears.

## Explicitly out of scope

- Zabbix trigger and template configuration for the target host
- EDA controller installation and project sync in AAP
- Claude Code CLI setup (covered in [04-claude-agent](04-claude-agent.md))
- Advanced rulebook patterns (multiple conditions, Level 0 vs Level 1 routing)
