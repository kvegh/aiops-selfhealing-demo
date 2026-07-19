# 06 -- EDA / Zabbix integration

This section connects Zabbix to Event-Driven Ansible so that alerts
automatically trigger the Claude agent via AAP. Zabbix ships a native
**Event-Driven Ansible** media type -- import it, point it at an AAP
Event Stream, and configure an action. No custom scripts or JavaScript
required.

AAP 2.7 uses **Event Streams** -- authenticated, gateway-managed
endpoints that replace raw `ansible.eda.webhook` port listeners. No
extra ports need to be exposed.

## Environment

- Zabbix 6.4+ with admin access (from [00-starting-setup](00-starting-setup.md))
- AAP 2.7 with EDA controller (from [00-starting-setup](00-starting-setup.md))
- EDA rulebook and playbook committed to a project repo synced in AAP

## Components

| Component | Purpose |
|-----------|---------|
| Zabbix media type | Ships with Zabbix -- sends alert payloads to EDA over HTTP |
| Zabbix trigger action | Fires the media type when a problem event occurs |
| AAP Event Stream | Secure, authenticated webhook endpoint managed by the AAP gateway |
| Event Stream credential | Authentication for the Event Stream (Basic Auth) |
| AAP credential (for EDA) | OAuth token so EDA can launch jobs on Controller |
| EDA rulebook activation | Binds the rulebook to the Event Stream and runs it |
| AAP job template | Runs the playbook that invokes Claude Code CLI |

## 1. EDA project and rulebook

### Project layout

AAP 2.7 scans for rulebooks at `extensions/eda/rulebooks/` in the
project root. Rulebooks placed elsewhere (e.g. `eda/`) will not be
discovered -- the project sync will report "This project contains no
rulebooks."

```
repo-root/
  extensions/
    eda/
      rulebooks/
        zabbix-webhook.yml
  playbooks/
    run_claude_analyse_fix.yml
```

### Rulebook

File: `extensions/eda/rulebooks/zabbix-webhook.yml`

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
      condition: 'event.payload.alert_name == "Linux: Zabbix agent is not available"'
      action:
        run_job_template:
          name: "Run Claude to analyse and fix"
          organization: "Default"
```

The source still says `ansible.eda.webhook` -- Event Streams replace
it with `ansible.eda.pg_listener` at activation time via source
mapping. The rulebook file itself stays generic.

> **YAML quoting:** If a condition value contains a colon followed by
> a space (e.g. `Linux: Zabbix`), the entire condition must be wrapped
> in single quotes. Otherwise YAML interprets the colon as a mapping
> key and the file fails to parse. The EDA project sync will silently
> report "no rulebooks" for invalid YAML.

## 2. Create an Event Stream credential

1. Navigate to **Automation Decisions --> Infrastructure --> Credentials**.
2. Click **Create credential**.
3. Set the fields:

| Field | Value |
|-------|-------|
| Name | `Zabbix Event Stream` |
| Organization | Default |
| Credential type | Basic Event Stream |
| Username | a username of your choice |
| Password | a password of your choice |

4. Click **Create credential**.

Note the username and password -- you will need them when configuring
the Zabbix media type.

## 3. Create an Event Stream

1. Navigate to **Automation Decisions --> Event Streams**.
2. Click **Create event stream**.
3. Set the fields:

| Field | Value |
|-------|-------|
| Name | `Zabbix Alerts` |
| Organization | Default |
| Event stream type | Basic Event Stream |
| Credential | `Zabbix Event Stream` (from step 2) |
| Forward events to rulebook activation | enabled |

4. Click **Create event stream**.

After creation, the Event Stream detail page shows a generated **URL**
-- copy it. This is the endpoint Zabbix will send alerts to.

> **Forward events toggle:** If disabled, the Event Stream operates in
> test mode -- it receives and displays events but does not forward
> them to rulebook activations. Enable it for production use.

## 4. Create a Controller OAuth token

EDA and Controller are separate services in AAP 2.7. When a rulebook
runs `run_job_template`, EDA needs an OAuth token to authenticate to
Controller.

1. In the AAP UI, click your username (top right) --> **Tokens**.
2. Click **Create Token**.
3. Set scope to **Write**.
4. Click **Create token** and copy the token value.

## 5. Create a Red Hat AAP credential for EDA

1. Navigate to **Automation Decisions --> Infrastructure --> Credentials**.
2. Click **Create credential**.
3. Set the fields:

| Field | Value |
|-------|-------|
| Name | `Controller Access` |
| Organization | Default |
| Credential type | Red Hat Ansible Automation Platform |
| Host | `https://YOUR_AAP_GATEWAY/api/controller` |
| OAuth Token | paste the token from step 4 |

4. Click **Create credential**.

> **Host URL:** In AAP 2.7 the Controller API sits behind the gateway
> at `/api/controller`. Using just the gateway hostname (e.g.
> `https://aap.example.com`) will fail with a 404 on
> `/api/v2/config/`. The correct value is
> `https://aap.example.com/api/controller`.

## 6. Create a Rulebook Activation

1. Navigate to **Automation Decisions --> Rulebook Activations**.
2. Click **Create rulebook activation**.
3. Set the fields:

| Field | Value |
|-------|-------|
| Name | `Zabbix Alert` |
| Organization | Default |
| Project | your synced EDA project |
| Rulebook | `zabbix-webhook.yml` |
| Credential | `Controller Access` (from step 5) |
| Decision environment | default or your custom DE |
| Restart policy | On failure |
| Rulebook activation enabled | checked |

4. After selecting the rulebook, the **Event streams** field becomes
   active. Click the **gear icon** to open the source mapping form.
5. In the mapping form:

| Field | Value |
|-------|-------|
| Rulebook source | `__SOURCE_1` |
| Event stream | `Zabbix Alerts` (from step 3) |

6. Click **Save** on the mapping, then **Create rulebook activation**.

The activation status should change to **Running** within a minute.
Check the History tab for logs if it fails.

> **Troubleshooting activation failures:** The activation logs
> (History tab) show the exact error. Common issues:
> - "no rulebooks" -- YAML parse error or wrong directory (see step 1)
> - 404 on `/api/v2/config/` -- wrong Host URL in the AAP credential (see step 5)
> - Event stream grayed out -- "Forward events to rulebook activation" is disabled on the Event Stream

## 7. Enable the Event-Driven Ansible media type in Zabbix

The Zabbix appliance ships the EDA media type pre-loaded -- no import
needed.

1. Navigate to **Alerts --> Media types**.
2. Filter for `ansible` -- the **Event-Driven Ansible** media type
   appears in the list.
3. Click on it to open the settings.
4. Ensure it is **Enabled**.

If you are not using the Zabbix appliance, you can import the media
type manually from the
[Zabbix integrations page](https://www.zabbix.com/integrations/ansible#event_driven_ansible)
or from the Zabbix installation directory
(`/usr/share/zabbix/zabbix_export/media_types/`).

### Update media type parameters for Event Streams

The default media type is designed for the old `ansible.eda.webhook`
approach (direct `host:port`). Two changes are needed for Event
Streams:

**a) Set the `endpoint` parameter to the Event Stream path.**

The media type script builds the URL as `send_to + endpoint`. The
default `endpoint` value is `/endpoint`. Change it to the path
portion of your Event Stream URL:

| Parameter | Value |
|-----------|-------|
| `endpoint` | `/eda-event-streams/api/eda/v1/external_event_stream/<uuid>/post/` |

Replace `<uuid>` with your Event Stream's UUID.

**b) Add Basic Auth credentials.**

Event Streams require authentication. The default media type script
does not send credentials. Add two new parameters:

| Parameter | Value |
|-----------|-------|
| `eda_username` | your Event Stream credential username |
| `eda_password` | your Event Stream credential password |

Then edit the **Script** section. In the `sendMessage` function, find
the line:

```javascript
request.addHeader('Content-Type: application/json');
```

Add this line immediately **before** it:

```javascript
request.addHeader('Authorization: Basic ' + btoa(Eda.params.eda_username + ':' + Eda.params.eda_password));
```

Save the media type.

> **URL split:** The script concatenates the user media's **Send to**
> field with the media type's `endpoint` parameter. The **Send to**
> field carries the base URL (e.g. `https://aap.example.com:443`)
> while `endpoint` carries the path. This split exists because
> different users might send to different hosts, while the path is
> shared. With Event Streams the path is per-stream, but the
> mechanism still works -- just put the full path in `endpoint`.

## 8. Configure a Zabbix user for EDA notifications

In production, create a dedicated Zabbix user for EDA notifications
with minimal permissions (read access to the relevant host groups).
In demo environments, an existing user with the required permissions
can be reused.

1. Navigate to **Users --> Users** and select the user (or create a
   new one).
2. In the user edit page, go to the **Media** tab, click **Add**.
3. Set the fields:

| Field | Value |
|-------|-------|
| Type | Event-Driven Ansible |
| Send to | `https://aap.example.com:443` (base URL only, no path) |
| Enabled | checked |

4. Click **Add**, then click **Update** on the user page to save.

> **Don't forget Update:** Adding the media entry is not enough --
> you must click **Update** on the user page or the media will not be
> saved.

5. Ensure the user has at least read permissions on the host groups
   you want to trigger on.

> **One user is enough:** The Zabbix documentation for the old
> `ansible.eda.webhook` approach says to create a separate user per
> rulebook (because each rulebook listens on a different port). With
> Event Streams this does not apply -- the gateway routes by the UUID
> in the URL, not by port. A single user can have multiple media
> entries pointing to different Event Stream URLs if needed.

## 9. Create a trigger action

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
| Send to users | Select the user from step 8 |
| Send only to | Event-Driven Ansible |

3. Save the action.

From this point, any Zabbix problem event matching the action
conditions will POST the alert payload to the Event Stream URL.

## 10. AAP job template and playbook

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

## 11. End-to-end flow

```
Zabbix trigger fires
    |
    v
Zabbix action matches --> sends via EDA media type
    |
    v
HTTPS POST to AAP Event Stream URL (gateway-managed, authenticated)
    |
    v
Event Stream forwards to EDA activation via pg_listener
    |
    v
EDA rulebook matches condition --> run_job_template
    |
    v
AAP Controller launches "Run Claude to analyse and fix"
    |
    v
Playbook runs on TRA VM as aaptra
    |
    v
Claude Code CLI diagnoses via MCP servers, remediates via AAP
```

## 12. Test the integration

### Manual Event Stream test

Simulate a Zabbix alert by posting directly to the Event Stream URL:

```bash
curl -X POST https://aap.example.com/eda-event-streams/api/eda/v1/external_event_stream/<uuid>/post/ \
  -u "username:password" \
  -H "Content-Type: application/json" \
  -d '{"alert_name": "Linux: Zabbix agent is not available", "host_name": "testserver1"}'
```

Replace the URL, username, and password with your Event Stream values.
Check the Event Stream detail page for received events, and the AAP
Controller for the launched job.

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
