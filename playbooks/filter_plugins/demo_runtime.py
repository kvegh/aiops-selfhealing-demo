"""Validate selected-instance settings after native Ansible Vault loading."""

import re

from ansible.errors import AnsibleFilterError
from ansible.utils.unsafe_proxy import wrap_var


ALLOWED_SETTINGS = {
    "hactar_source_git_token",
    "demo_website_dns_api_token",
    "demo_website_fault_template_id",
    "demo_website_webhook_key",
    "demo_website_zabbix",
    "demo_zabbix_clone_api_token",
    "demo_zabbix_dns_api_token",
    "demo_zabbix_basic_auth_file",
    "demo_zabbix_event_stream",
    "demo_zabbix_mcp_api_token",
    "demo_claude_vertex_auth",
    "demo_aap_mcp",
    "demo_mcp_subscription",
    "demo_cloudcli_deployment",
}


def _literal_data(value):
    # Core 2.20 can pass lazy list subclasses to filters. wrap_var rebuilds
    # sequences with type(value), which those internal containers prohibit.
    if isinstance(value, dict):
        return {wrap_var(key): _literal_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_literal_data(item) for item in value]
    return wrap_var(value)


def selected_settings(value, instance):
    message = "Runtime settings must contain only reviewed inputs for the selected AAP instance."
    if not isinstance(instance, str) or not re.fullmatch(r"aap27-test-[1-9][0-9]*", instance):
        raise AnsibleFilterError(message + " Invalid selected instance.")
    if not isinstance(value, dict) or set(value) != {"schema_version", "instances"}:
        raise AnsibleFilterError(message + " Invalid document fields.")
    # Native core 2.20 YAML integers carry tags; bool must still be refused.
    if (not isinstance(value["schema_version"], int) or isinstance(value["schema_version"], bool)) or value["schema_version"] != 1:
        raise AnsibleFilterError(message + " Unsupported schema version.")
    if not isinstance(value["instances"], dict) or instance not in value["instances"]:
        raise AnsibleFilterError(message + " Missing selected namespace.")
    for name, settings in value["instances"].items():
        if (not isinstance(name, str) or not re.fullmatch(r"aap27-test-[1-9][0-9]*", name)
                or not isinstance(settings, dict) or set(settings) - ALLOWED_SETTINGS):
            raise AnsibleFilterError(message + " Unreviewed namespace or setting name.")
    # Settings are data. In particular, credential text must never become a
    # second Jinja template after the native Vault loader decrypts it.
    return _literal_data(value["instances"][instance])


class FilterModule:
    def filters(self):
        return {"demo_runtime_selected_settings": selected_settings}
