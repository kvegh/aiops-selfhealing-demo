# Big Bad Button: paused AAP dashboard extension

Checkpoint date: 2026-10-17. This document is the starting point for another
chat continuing the unfinished dashboard work. Read it with the repository
README and [website recreation guide](07-audience-website-demo.md). No previous
chat transcript or temporary helper script is required for this handoff.

## Working baseline and scope

The existing button → fault job → Zabbix problem → EDA repair → Zabbix
recovery → EDA rearm loop was tested successfully. Its recreation guide records
the prior lifecycle and ten-press rehearsals. The user subsequently confirmed
that the repair job works well live with its existing timing.

The proposed extra ten-second pause at the start of
`playbooks/restore_website_content.yml` was cancelled and removed before it
was deployed. That playbook has no timing change in this checkpoint. Do not
reintroduce the pause when resuming the dashboard work.

The unfinished request is to extend the existing native Zabbix dashboard with:

- The cumulative event count of the selected AAP EDA Event Stream.
- The latest five Big Bad Button jobs and their statuses.
- The count and latest five records of currently running Big Bad Button jobs.

The job panels must be limited to the five BBB lifecycle/fault/repair/rearm
templates listed in encrypted settings. The Event Stream counter covers the
whole selected stream, which can also receive other demo events. A successful
Zabbix delivery, the stream's received count, and EDA rule/job execution are
different observations; the counter does not prove that a rule matched.

## What has been prepared

| File | Purpose |
| --- | --- |
| `src/configure_aap_monitoring.py` | Loads encrypted settings using installed `ansible-inventory`; creates or updates the dedicated Zabbix host, secret macro, seven items, and existing dashboard |
| `src/aap_dashboard/stream_summary.js` | Retains only the received count and last event timestamp |
| `src/aap_dashboard/jobs_summary.js` | Retains only job ID, name, status, start and finish timestamps |
| `src/aap_dashboard/jobs_table.js` | Escapes job fields before rendering a native HTML item-history table |
| `tests/aap_dashboard_preprocessing.test.js` | Checks response validation, omission of unrelated secret fields, HTML escaping, and the empty running-job display |
| `assets/zabbix/website-deliveries-dashboard.json.j2` | Six-widget dashboard request with generic placeholders |
| `myvars` | Ansible Vault-encrypted integration values and credentials |

The helper reuses the host with technical name `demo-aap-dashboard` and visible
name **AAP demo monitoring**. Its host group, existing map, dashboard, actions,
media type, presenter, stream and template IDs come from encrypted settings.
It expects the existing **Big Bad Button - EDA Deliveries** dashboard to have
one page and refuses to replace unexpected extra widgets. It updates pages
without requesting ownership or sharing changes. Configuration readback checks
widget geometry, fields, dashboard name, owner and private status.

The dashboard has six widgets, all refreshing every ten seconds:

| Widget | Position and size (Zabbix grid units) |
| --- | --- |
| Website health | x=0, y=0, width=36, height=8 |
| Events received by EDA | x=36, y=0, width=18, height=3 |
| BBB jobs running count | x=54, y=0, width=18, height=3 |
| Recent BBB jobs | x=36, y=3, width=36, height=5 |
| Zabbix to EDA deliveries | x=0, y=8, width=36, height=5 |
| Currently running BBB jobs | x=36, y=8, width=36, height=5 |

The helper creates these items:

| Key | Data |
| --- | --- |
| `aap.demo.stream.summary` | HTTP agent master, selected Event Stream summary |
| `aap.demo.stream.events_received` | Dependent unsigned received count |
| `aap.demo.jobs.recent` | HTTP agent master, latest five selected-template jobs |
| `aap.demo.jobs.recent_table` | Dependent escaped HTML table |
| `aap.demo.jobs.running` | HTTP agent master, selected-template jobs with status `running` |
| `aap.demo.jobs.running_count` | Dependent unsigned running count |
| `aap.demo.jobs.running_table` | Dependent escaped HTML table |

The three HTTP masters poll every four seconds, require HTTP 200, and verify
both TLS certificate trust and hostname. They authenticate using the host's
secret `{$BBB.AAP.TOKEN}` macro. The API paths are:

```text
/api/eda/v1/event-streams/<stream-id>/
/api/controller/v2/jobs/?job_template__in=<template-ids>&order_by=-id&page_size=5
/api/controller/v2/jobs/?job_template__in=<template-ids>&order_by=-id&page_size=5&status=running
```

Recent-job results are the latest jobs regardless of their start date; the
widget's rolling five-minute period selects fresh polling snapshots. Running
counts exclude queued/pending jobs. Very short jobs can finish between a
four-second API poll or ten-second widget refresh; the recent-job table is
the retained record. No artificial repair delay is planned.

## Last observed live state and blocker

During the 2026-10-14 setup, an AAP gateway read-scope token was created and
verified with authenticated GET requests to the Controller and EDA APIs. It
was saved in encrypted `myvars`; the gateway token ID is stored there too.
The new Zabbix host, macros, seven items and dashboard widgets were created,
and their saved configuration was read back successfully.

Data collection did not succeed. The new items were unsupported, with:

```text
Cannot perform request: SSL certificate problem: unable to get local issuer certificate
```

They had no collected samples (`lastclock` was zero). A default displayed
zero must not be interpreted as a genuine received/running count.

TLS verification from the operator workspace succeeded. The AAP endpoint used
a certificate issued by its private AAP CA, and the server sent its leaf
certificate. The likely cause is that the Zabbix server lacks the trusted CA;
that diagnosis still needs confirmation on the actual polling server or proxy.
No CA-trust change was made and TLS verification was not disabled.

These are historical observations, not a fresh assertion about the current
live state. This checkpoint only saves work; it does not rerun configuration,
deploy playbooks, launch jobs, restart services, or change the demo's enabled
state.

## Encrypted settings

Use the existing project Vault password file (`vpf` in the operator workspace).
It is not committed. All environment-specific values remain inside `myvars`.
The lifecycle keys are:

```text
demo_zabbix_api_url
demo_zabbix_api_token
demo_zabbix_item_id
demo_zabbix_trigger_id
```

The dashboard extension adds:

```text
demo_aap_api_url
demo_aap_dashboard_api_token
demo_aap_dashboard_token_id
demo_aap_event_stream_id
demo_aap_job_template_ids
demo_zabbix_demo_dashboard_id
demo_zabbix_demo_host_group_id
demo_zabbix_website_map_id
demo_zabbix_presenter_user_id
demo_zabbix_problem_action_id
demo_zabbix_recovery_action_id
demo_zabbix_media_type_id
```

The source helper and encrypted settings replace any dependence on earlier
temporary scripts. It prints configuration IDs and verification status, not
credentials. Do not print decrypted settings or tokens during diagnosis.
Existing environment SSH/MCP connections and trusted CA material are external
access prerequisites; this repository and `vpf` do not provision a new lab.

## Resume checklist

1. Inspect current Git and live configuration before making changes. Use the
   encrypted URLs and IDs to identify the integrations. Verify any configured
   AAP MCP connection before relying on it; Zabbix MCP was read-only, so the
   Zabbix API credential in `myvars` was used for configuration.
2. Inspect the new items' support status, errors, and actual recent sample
   timestamps. Confirm which Zabbix server/proxy polls these HTTP items.
3. Confirm the AAP certificate chain and the poller's CA configuration. Obtain
   the issuing CA through an authenticated trusted source, then configure the
   poller's trust appropriately using authorized host access. Keep certificate
   and hostname verification enabled; do not substitute an unverified leaf
   certificate or bypass an access failure. Read-only SSH attempts in the
   workspace sandbox previously failed on system SSH configuration ownership;
   use the normal approved execution path rather than bypassing SSH checks.
4. If configuration needs to be recreated or updated, use the saved helper
   after reviewing its prerequisites. This command writes Zabbix configuration
   and expects the existing dashboard and supporting objects:

   ```bash
   python3 -B src/configure_aap_monitoring.py --vault-password-file /path/to/vpf
   ```

   It needs the existing Python standard library and installed Ansible binary;
   no new package or virtual environment is required.
5. Verify real supported samples for all seven items, correct Event Stream
   count and job filtering, and actual browser rendering/refresh of the six
   widgets. Confirm the existing dashboard owner/sharing, website monitor and
   notification filters remain correct. Saved widget fields alone are not
   evidence that data or the rendered display works.
6. When live demo testing is authorized again, use one complete normal button
   cycle to verify the stream count, recent jobs, repair, recovery-driven
   rearm and new nonce. The page POSTs JSON with the `nonce` field to
   `/api/panic`; preserve the body format because nginx delivery locking keys
   on that body. Inspect the resulting jobs through completion. Do not repeat
   the earlier disable/enable/concurrency rehearsal just to save this handoff.
7. Record the actual results and implementation revision, update these status
   notes, and commit/push the completed fix. Preserve the requested final demo
   state. The cancelled ten-second repair pause is not an outstanding task.

## Checkpoint validation

Local validation for this checkpoint covers the preprocessing tests, Python
syntax, rendered dashboard JSON/layout and encrypted Vault readability. These
checks do not claim successful live collection or a new end-to-end rehearsal.
All of those local checks passed on 2026-10-17. The repair playbook was also
verified to match its previously committed version, without the cancelled
pause. The dashboard check confirmed six non-overlapping widgets, private
ownership configuration, ten-second refresh fields and valid local doc links.
Run the JavaScript checks with the existing Node binary:

```bash
node tests/aap_dashboard_preprocessing.test.js
git diff --check
```

Generated Python bytecode is ignored and is not part of the saved work.
Token rotation, job-template review/labels, and shared/project Vault cleanup
remain deferred in the [design backlog](todo/demo-design.md).
