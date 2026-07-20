# Mistakes

Factually wrong content in the repo.

---

## 1. ✅ Doc 06 rulebook example uses wrong field name and operator — fixed in inconsistency #2

The inline rulebook in doc 06 uses:

```yaml
condition: event.payload.alert_name == "Linux: Zabbix agent is not available (for 3m)"
```

The actual deployed rulebook and troubleshooting.md both confirm it should be:

```yaml
condition: event.payload.event_name is search("Zabbix agent is not available")
```

Three errors in one line:
- `alert_name` → `event_name` (wrong field from the Zabbix payload)
- `==` → `is search()` (exact match breaks on Zabbix's dynamic suffix like `(for 3m)`)
- Full string with suffix → substring without suffix (the duration changes)

## 2. ✅ Doc 04 heading number is wrong — fixed in inconsistency #5

`04-claude-agent.md` starts with `# 02 – Set up Claude agent`. The heading number should be 04 to match the filename.

## 3. ✅ Doc 05 heading number is wrong — fixed in inconsistency #5

`05-cloudcli-web-ui.md` starts with `# 07 – CloudCLI Web UI`. The heading number should be 05 to match the filename.

## 4. ✅ README repo layout claims nonexistent directories — fixed in gap #1

`docs/build/`, `rulebooks/`, and `config/` are listed in the README but do not exist in the repository. See gaps_new.md #1 for the full diff.

## 5. ✅ Doc 06 intro is misleading — not an issue, see inconsistency #9

The introduction says "No custom scripts or JavaScript required" but section 7 of the same doc requires editing the media type JavaScript to add a Basic Auth header. The statement should be qualified — e.g., "no custom webhook scripts" — because as written it contradicts content two sections later.
