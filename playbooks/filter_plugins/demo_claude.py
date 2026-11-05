"""Validate the pinned native Claude program before any managed installation."""

import copy
import json
import ipaddress
from pathlib import Path
import re
import ssl
from urllib.parse import urlsplit
import yaml

from ansible.errors import AnsibleFilterError
from ansible.utils.unsafe_proxy import wrap_var


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def release(value):
    require(isinstance(value, dict), "Supply the reviewed native Claude release pin.")
    version = value.get("version", "")
    require(isinstance(version, str)
            and re.fullmatch(r"[1-9][0-9]{0,3}\.(?:0|[1-9][0-9]{0,3})\.(?:0|[1-9][0-9]{0,5})", version),
            "Select an exact Claude version rather than a moving release channel.")
    expected = f"https://downloads.claude.ai/claude-code-releases/{version}/linux-x64/claude"
    require(value.get("platform") == "linux-x64" and value.get("url") == expected,
            "Use only the reviewed official Linux x64 native release URL.")
    require(isinstance(value.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", value["sha256"])
            and type(value.get("bytes")) is int and 0 < value["bytes"] <= 1024 ** 3,
            "Pin the official binary SHA-256 and exact positive size.")
    return {key: value[key] for key in ("version", "platform", "url", "sha256", "bytes")}


def existing_program(stat, pin):
    """Adopt only the exact root-owned pin; preserve other installations for review."""
    expected = release(pin)
    require(isinstance(stat, dict), "Inspect the existing command before installation.")
    if stat.get("exists") is False:
        return True
    require(stat.get("exists") is True and stat.get("isreg") is True
            and not stat.get("islnk", False) and stat.get("uid") == 0
            and stat.get("mode") == "0755"
            and stat.get("checksum") == expected["sha256"]
            and stat.get("size") == expected["bytes"],
            "Preserve the different or unowned Claude command and review it before replacement.")
    return True


def vertex(value, home):
    require(isinstance(value, dict) and set(value) == {"project_id", "region", "adc"},
            "Supply only the approved selected-instance Vertex configuration.")
    require(isinstance(home, str) and Path(home).is_absolute() and str(Path(home)) == home
            and home not in ("/", "/root") and ".." not in Path(home).parts,
            "Use the verified runtime account's actual home.")
    require(isinstance(value["project_id"], str)
            and re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", value["project_id"])
            and isinstance(value["region"], str) and re.fullmatch(r"[a-z][a-z0-9-]{1,40}", value["region"]),
            "Require an explicit Vertex project and region.")
    adc = value["adc"]
    allowed = {"type", "client_id", "client_secret", "refresh_token", "quota_project_id",
               "universe_domain", "account", "token_uri"}
    require(isinstance(adc, dict) and not set(adc) - allowed and adc.get("type") == "authorized_user"
            and all(isinstance(item, str) for item in adc.values())
            and all(isinstance(adc.get(key), str) and adc[key]
                    for key in ("client_id", "client_secret", "refresh_token", "quota_project_id"))
            and adc.get("universe_domain", "googleapis.com") == "googleapis.com"
            and adc.get("token_uri", "https://oauth2.googleapis.com/token") == "https://oauth2.googleapis.com/token",
            "Use only the explicitly approved Google authorized-user ADC with its quota project.")
    return wrap_var({"adc": copy.deepcopy(adc), "environment": {
        "CLAUDE_CODE_USE_VERTEX": "1", "ANTHROPIC_VERTEX_PROJECT_ID": value["project_id"],
        "CLOUD_ML_REGION": value["region"],
        "GOOGLE_APPLICATION_CREDENTIALS": home + "/.config/gcloud/application_default_credentials.json",
        "DISABLE_AUTOUPDATER": "1",
    }})


def vertex_settings(text, config, native_auth_exists=False):
    try:
        result = json.loads(text) if text.strip() else {}
        require(isinstance(result, dict) and isinstance(result.get("env", {}), dict),
                "Preserve invalid existing Claude settings for review.")
        env = result.setdefault("env", {})
        require(type(native_auth_exists) is bool and (not native_auth_exists or (
            env.get("CLAUDE_CODE_USE_VERTEX") == "1"
            and env.get("ANTHROPIC_VERTEX_PROJECT_ID") == config["environment"]["ANTHROPIC_VERTEX_PROJECT_ID"])),
            "Preserve existing native Claude authentication before selecting another provider.")
        require(not result.get("apiKeyHelper")
                and not any(str(env.get(key, "")).lower() not in ("", "0", "false")
                            for key in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_FOUNDRY"))
                and not any(env.get(key) for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")),
                "Preserve conflicting existing provider authentication for explicit review.")
        for key, value in config["environment"].items():
            require(key not in env or env[key] == value,
                    "Preserve conflicting existing Vertex settings for explicit review.")
            env[key] = value
        return wrap_var(result)
    except (ValueError, TypeError, AttributeError, KeyError):
        raise AnsibleFilterError("Preserve invalid existing Claude settings for review.") from None


def existing_adc(text, config):
    try:
        require(json.loads(text) == config["adc"],
                "Preserve the different existing Google ADC and review its ownership.")
        return True
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError("Preserve invalid existing Google ADC for review.") from None


def aap_mcp(value, instance):
    """Use only the selected instance's private authenticated MCP connection."""
    require(isinstance(value, dict) and set(value) == {"instance_name", "url", "ca_pem", "token"}
            and value["instance_name"] == instance,
            "Backfill only this selected instance's API/MCP token and CA, then refresh AIOps CaC.")
    try:
        parsed = urlsplit(value["url"])
        address = ipaddress.IPv4Address(parsed.hostname)
        require(value["url"] == "https://" + str(address) + ":8448/mcp"
                and any(address in ipaddress.IPv4Network(network)
                        for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")),
                "Use only the selected private AAP MCP address with certificate verification.")
        require(isinstance(value["token"], str) and 16 <= len(value["token"]) <= 4096
                and re.fullmatch(r"[A-Za-z0-9._~+/=-]+", value["token"]),
                "Use the selected existing API/MCP bearer without credential fallback.")
        authority = value["ca_pem"]
        require(isinstance(authority, str) and len(authority) <= 524288 and "PRIVATE KEY" not in authority,
                "Use only the selected installed public authority.")
        blocks = re.findall(r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----", authority)
        require(bool(blocks), "Require the verified selected public certificate authority.")
        pem = "\n".join(blocks) + "\n"
        ssl.create_default_context(cadata=pem)
        return wrap_var({"definition": {"type": "http", "url": value["url"],
            "headers": {"Authorization": "Bearer " + value["token"]}},
            "ca_pem": pem, "api_origin": "https://" + str(address)})
    except (ValueError, TypeError, KeyError, ssl.SSLError):
        raise AnsibleFilterError("The selected private AAP MCP authority or endpoint is invalid.") from None


def aap_client(text, project, definition):
    try:
        result = json.loads(text) if text.strip() else {}
        require(isinstance(result, dict), "Preserve invalid existing client configuration for review.")
        selected = result.setdefault("projects", {}).setdefault(project, {}).setdefault("mcpServers", {})
        require("aap-mcp" not in selected or selected["aap-mcp"] == definition,
                "Preserve the different existing AAP MCP entry; review its target and authentication.")
        selected["aap-mcp"] = copy.deepcopy(definition)
        return wrap_var(result)
    except (ValueError, TypeError, AttributeError):
        raise AnsibleFilterError("Preserve invalid existing client configuration for review.") from None


def agent_servers(text, project, definition):
    try:
        servers = json.loads(text)["projects"][project]["mcpServers"]
        require(servers.get("aap-mcp") == definition, "The installed private AAP MCP entry changed.")
        for name in ("linux-mcp", "zabbix"):
            row = servers[name]
            require(row.get("type", "stdio") == "stdio" and row.get("command") == "podman"
                    and "--pull=never" in row.get("args", []), "Use only the installed private MCP definitions.")
        return wrap_var({"mcpServers": {name: copy.deepcopy(servers[name])
                                       for name in ("linux-mcp", "zabbix", "aap-mcp")}})
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError("The selected private MCP configuration is incomplete.") from None


def repair_template(value, inventory, project):
    """Resolve the one existing saved repair; never accept caller target overrides."""
    require(type(inventory) is int and inventory > 0 and type(project) is int and project > 0,
            "Run from the existing AAP job's native inventory and project.")
    require(isinstance(value, dict) and value.get("count") == 1 and value.get("next") is None
            and len(value.get("results", [])) == 1, "Resolve exactly one existing selected repair template.")
    row = value["results"][0]
    require(type(row.get("id")) is int and row["id"] > 0 and row.get("name") == "Deploy Zabbix Agent"
            and row.get("playbook") == "playbooks/deploy_zabbix_agent.yml" and row.get("limit") == "testserver1"
            and row.get("inventory") == inventory and row.get("project") == project
            and all(row.get(key) is False for key in ("ask_inventory_on_launch", "ask_limit_on_launch",
                "ask_variables_on_launch", "ask_credential_on_launch")),
            "The repair must use its saved selected inventory, testserver limit and credentials without overrides.")
    return row["id"]


def linux_alias(text, target):
    expected = {"HostName": target["address"], "User": target["user"], "Port": str(target["port"]),
        "IdentityFile": "/var/lib/mcp/.ssh/id_ed25519", "UserKnownHostsFile": "/var/lib/mcp/.ssh/known_hosts",
        "StrictHostKeyChecking": "yes", "IdentitiesOnly": "yes"}
    try:
        rows = [line.strip().split(None, 1) for line in text.splitlines() if line.strip()]
        require(rows[0] == ["Host", "testserver1"] and len(rows) == len(expected) + 1
                and dict(rows[1:]) == expected, "The installed SSH alias must identify only this verified testserver.")
        return "testserver1"
    except (ValueError, IndexError, TypeError):
        raise AnsibleFilterError("The installed SSH alias differs from the verified selected testserver.") from None


def repair_host(value, target, instance):
    require(isinstance(value, dict) and value.get("count") == 1 and value.get("next") is None
            and len(value.get("results", [])) == 1, "Resolve exactly one selected repair inventory host.")
    row = value["results"][0]
    try:
        variables = row["variables"]
        variables = yaml.safe_load(variables) if isinstance(variables, str) else variables
        resource = variables["demo_managed_guest"]
        require(row.get("name") == "testserver1" and variables.get("demo_instance_name") == instance
                and variables.get("ansible_host") == target["address"]
                and variables.get("ansible_user") == target["user"]
                and str(variables.get("ansible_port")) == str(target["port"])
                and all(resource.get(key) == target[key] for key in
                        ("vm_name", "uuid", "address", "mac", "machine_id", "hypervisor_machine_id", "host_keys", "verified")),
                "The saved repair host must match this selected guest's native identity and SSH connection.")
        return True
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError("The selected repair inventory host is incomplete or belongs to another guest.") from None


def agent_report(text):
    try:
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
        terminal = [row for row in events if row.get("type") == "result"]
        require(len(terminal) == 1 and terminal[0].get("subtype") == "success"
                and terminal[0].get("is_error") is False, "The bounded agent did not complete successfully.")
        messages = [part["text"] for row in events if row.get("type") == "assistant"
                    for part in row.get("message", {}).get("content", []) if part.get("type") == "text"]
        require(bool(messages), "The bounded agent returned no readable incident report.")
        return messages
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError("The bounded agent output is not a complete ordered JSON stream.") from None


def launched_repairs(text, repair):
    """Read actual native launch responses, never IDs asserted in model prose."""
    try:
        events = [json.loads(line) for line in text.splitlines() if line.strip()]
        calls, results = {}, {}
        for row in events:
            for part in row.get("message", {}).get("content", []):
                if part.get("type") == "tool_use" and part.get("name") == "mcp__aap-mcp__job_templates_launch_create":
                    arguments = part["input"]
                    require(str(arguments.get("id")) == str(repair)
                            and set(arguments) <= {"id", "requestBody"} and arguments.get("requestBody") in (None, {}),
                            "Only the prechecked repair can be launched without overrides.")
                    calls[part["id"]] = arguments
                if part.get("type") == "tool_result":
                    results[part["tool_use_id"]] = part
        require(len(calls) <= 2, "The supported agent demo permits at most two repair cycles.")
        identities = []
        for identity in calls:
            result = results[identity]
            require(not result.get("is_error"), "The native repair launch returned an error.")
            content = result["content"]
            if isinstance(content, list):
                content = next(part["text"] for part in content if part.get("type") == "text")
            value = json.loads(content) if isinstance(content, str) else content
            if isinstance(value, dict) and isinstance(value.get("content"), list):
                value = json.loads(next(part["text"] for part in value["content"] if part.get("type") == "text"))
            if isinstance(value, dict) and isinstance(value.get("structuredContent"), dict):
                value = value["structuredContent"]
            if isinstance(value, dict) and isinstance(value.get("result"), dict):
                value = value["result"]
            require(isinstance(value, dict), "Read the actual native repair launch response.")
            job = value.get("job", value.get("id"))
            require(type(job) is int and job > 0 and value.get("id", job) == job
                    and value.get("job_template", repair) == repair,
                    "The repair response must identify the selected template's actual child job.")
            identities.append(job)
        require(len(set(identities)) == len(identities), "Each repair launch needs its own native child job.")
        return identities
    except (ValueError, TypeError, KeyError, StopIteration):
        raise AnsibleFilterError("The agent stream has no verifiable native repair response.") from None


def agent_incident(value, expected):
    try:
        rows = value["result"]
        require(len(rows) == 1 and rows[0]["host"] == expected and rows[0]["status"] == "0",
                "Resolve only the selected enabled monitored testserver.")
        row = rows[0]
        triggers = [item for item in row["triggers"] if "Zabbix agent is not available" in item["description"]
                    and item["status"] == "0"]
        require(len(triggers) == 1 and triggers[0]["value"] == "1",
                "This bounded demo supports only the selected active agent-unavailable incident.")
        return {"host_id": row["hostid"], "trigger_id": triggers[0]["triggerid"]}
    except (ValueError, TypeError, KeyError):
        raise AnsibleFilterError("The selected supported agent incident is unavailable.") from None


def monitoring_recovered(value, expected, incident, minimum_clock):
    """Require a fresh actual sample and recovery of the exact original trigger."""
    try:
        rows = value["result"]
        if len(rows) != 1:
            return False
        row = rows[0]
        items = [item for item in row["items"] if item["key_"] == "agent.ping"]
        triggers = [item for item in row["triggers"] if item["triggerid"] == incident["trigger_id"]]
        return (row["host"] == expected and row["hostid"] == incident["host_id"] and row["status"] == "0"
                and len(items) == len(triggers) == 1 and items[0]["status"] == items[0]["state"] == "0"
                and str(items[0]["lastclock"]).isascii() and str(items[0]["lastclock"]).isdigit()
                and int(items[0]["lastclock"]) >= int(minimum_clock) and float(items[0]["lastvalue"]) == 1
                and triggers[0]["status"] == triggers[0]["value"] == "0")
    except (ValueError, TypeError, KeyError):
        return False


class FilterModule:
    def filters(self):
        return {"demo_claude_release": release, "demo_claude_existing_program": existing_program,
                "demo_claude_vertex": vertex, "demo_claude_vertex_settings": vertex_settings,
                "demo_claude_existing_adc": existing_adc, "demo_claude_aap_mcp": aap_mcp,
                "demo_claude_aap_client": aap_client, "demo_claude_agent_servers": agent_servers,
                "demo_claude_repair_template": repair_template, "demo_claude_linux_alias": linux_alias,
                "demo_claude_agent_report": agent_report,
                "demo_claude_repair_host": repair_host, "demo_claude_launched_repairs": launched_repairs,
                "demo_claude_agent_incident": agent_incident, "demo_claude_monitoring_recovered": monitoring_recovered}
