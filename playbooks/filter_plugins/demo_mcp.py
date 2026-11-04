"""Bind stdio MCP deployment to verified guests and local offline artifacts."""

import copy
import importlib.util
import ipaddress
import json
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit

from ansible.errors import AnsibleFilterError

SPEC = importlib.util.spec_from_file_location("mcp_website_schema", Path(__file__).with_name("demo_website.py"))
website = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(website)

IMAGES = {
    "linux-mcp": "quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest",
    "zabbix-mcp": "localhost/zabbix-mcp-server:latest",
}


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def guest(config, value, role):
    require(isinstance(value, dict) and value.get("verified") is True,
            "The selected guest must have verified creation metadata.")
    expected = f"{role}-v{config['instance_number']:02d}"
    require(value.get("vm_name") == expected
            and value.get("hypervisor_machine_id") == config["hypervisor"]["machine_id"],
            "The guest must belong to this instance and its selected hypervisor.")
    try:
        address = ipaddress.IPv4Address(value["address"])
        require(address.is_private and not address.is_loopback and not address.is_link_local,
                "Use only the selected guest's private address.")
        require(str(uuid.UUID(value["uuid"])) == value["uuid"], "Require the guest's verified UUID.")
        require(re.fullmatch(r"[0-9a-f]{32}", value["machine_id"]), "Require the guest's machine identity.")
        require(re.fullmatch(r"[a-z_][a-z0-9_-]*", value["user"]) and value["user"] != "root",
                "Use the existing non-root guest management account.")
        keys = [" ".join(str(key).split()[:2]) for key in value["host_keys"]]
        checked = website.website_configuration(dict(
            config, aap_fqdn=config["aap_hostname"], hypervisor=dict(
                config["hypervisor"], address=str(address), user=value["user"],
                port=value["port"], machine_id=value["machine_id"], host_keys=keys,
            ),
        ))
        return dict(value, address=str(address), port=checked["hypervisor"]["port"], host_keys=keys)
    except (KeyError, TypeError, ValueError):
        raise AnsibleFilterError("Invalid selected guest identity; no previous target may be substituted.") from None


def artifact_manifest(value, number):
    require(isinstance(value, dict) and value.get("schema_version") == 1
            and value.get("counter") == number and not isinstance(value.get("counter"), bool),
            "Supply the verified offline artifact manifest for this same allocation.")
    root = f"/opt/aiops-mcp-artifacts/v{number:02d}"
    images = {}
    for kind, name in IMAGES.items():
        rows = [row for row in value.get("images", []) if row.get("name") == name]
        require(len(rows) == 1, "Each approved MCP image needs one verified local archive.")
        row = rows[0]
        identity = str(row.get("image_id", "")).removeprefix("sha256:")
        require(row.get("archive") == f"{root}/{kind}.tar"
                and re.fullmatch(r"[0-9a-f]{64}", identity)
                and re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", "")))
                and isinstance(row.get("bytes"), int) and row["bytes"] > 0,
                "Image identity, exact local archive path, SHA-256 and size are required.")
        images[kind] = dict(row, image_id="sha256:" + identity)
    rpms = value.get("rpms", [])
    require(isinstance(rpms, list) and rpms, "Stage the signed rootless Podman RPM closure first.")
    for row in rpms:
        path = str(row.get("path", ""))
        require(path.startswith(root + "/rpms/") and Path(path).name.endswith(".rpm")
                and str(Path(path)) == path and ".." not in Path(path).parts
                and re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", "")))
                and row.get("signature_verified") is True
                and isinstance(row.get("nevra"), str) and row["nevra"]
                and isinstance(row.get("bytes"), int) and row["bytes"] > 0,
                "Every runtime RPM must have a verified signature, local path, SHA-256 and size.")
    require(len({row["path"] for row in rpms}) == len(rpms), "Runtime RPM paths must be unique.")
    return {"images": images, "rpms": copy.deepcopy(rpms),
            "minimum_free_bytes": max(2 * 1024 ** 3, 3 * sum(row["bytes"] for row in images.values())
                                      + sum(row["bytes"] for row in rpms))}


def configuration(value):
    config = website.website_configuration(value)
    require(isinstance(value, dict), "Select the existing instance's MCP deployment metadata.")
    config["tra"] = guest(config, value.get("tra"), "tra")
    config["testserver"] = guest(config, value.get("testserver"), "testserver1")
    config["artifacts"] = artifact_manifest(value.get("artifacts"), config["instance_number"])
    return config


def user_record(output, expected):
    fields = output.strip().split(":")
    require(len(fields) == 7 and fields[0] == expected and fields[2].isdigit()
            and int(fields[2]) > 0 and fields[3].isdigit() and fields[5].startswith("/home/")
            and ".." not in Path(fields[5]).parts,
            "Use the existing non-root guest account and its actual home directory.")
    return {"name": fields[0], "uid": int(fields[2]), "gid": int(fields[3]), "home": fields[5]}


def subordinate_range(text, user):
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) == 3 and parts[0] in {user["name"], str(user["uid"])}:
            if parts[1].isdigit() and parts[2].isdigit() and int(parts[2]) >= 65536:
                return True
    return False


def client_configuration(text, project, name, definition):
    try:
        config = json.loads(text) if text.strip() else {}
        require(isinstance(config, dict), "The existing Claude configuration must be a JSON object.")
        projects = config.setdefault("projects", {})
        selected = projects.setdefault(project, {})
        selected.setdefault("mcpServers", {})[name] = definition
        return config
    except (ValueError, TypeError, AttributeError):
        raise AnsibleFilterError("Preserve the invalid existing client configuration for review.") from None


def zabbix_configuration(value, token):
    config = website.website_configuration(value)
    target = value.get("zabbix", {})
    require(isinstance(target, dict) and target.get("instance_name") == config["instance_name"]
            and target.get("instance_number") == config["instance_number"]
            and target.get("vm_name") == f"zabbix-v{config['instance_number']:02d}"
            and target.get("hypervisor_machine_id") == config["hypervisor"]["machine_id"],
            "Use the verified Zabbix clone belonging to this same allocation and hypervisor.")
    try:
        address = ipaddress.IPv4Address(target["address"])
        url = urlsplit(target["api_url"])
        require(address.is_private and not address.is_loopback and not address.is_link_local
                and url.scheme == "http" and url.netloc == str(address)
                and url.path == "/api_jsonrpc.php" and not url.query and not url.fragment,
                "Use only the verified new Zabbix guest's private API.")
        require(isinstance(token, str) and len(token.strip()) > 20,
                "Supply the explicitly selected new target's MCP token.")
        return {"origin": "http://" + str(address), "token": token}
    except (KeyError, TypeError, ValueError):
        raise AnsibleFilterError("The new target's Zabbix API metadata is incomplete.") from None


class FilterModule:
    def filters(self):
        return {
            "demo_mcp_configuration": configuration,
            "demo_mcp_user_record": user_record,
            "demo_mcp_subordinate_range": subordinate_range,
            "demo_mcp_client_configuration": client_configuration,
            "demo_mcp_zabbix_configuration": zabbix_configuration,
        }
