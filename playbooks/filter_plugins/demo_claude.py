"""Validate the pinned native Claude program before any managed installation."""

import copy
import json
from pathlib import Path
import re

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


class FilterModule:
    def filters(self):
        return {"demo_claude_release": release, "demo_claude_existing_program": existing_program,
                "demo_claude_vertex": vertex, "demo_claude_vertex_settings": vertex_settings,
                "demo_claude_existing_adc": existing_adc}
