"""Exercise target/artifact boundaries and real stdio verification without services."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from ansible.errors import AnsibleFilterError


ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


FILTERS = module("mcp_filters", ROOT / "playbooks/filter_plugins/demo_mcp.py")
VERIFIER = module("mcp_verifier", ROOT / "src/verify_stdio_mcp.py")


def deployment():
    number = 7
    result = {
        "instance_name": "aap27-test-7", "instance_number": number,
        "zone": "example.com", "aap_fqdn": "aap27.v07.example.com",
        "hypervisor": {"name": "recovery", "address": "8.8.8.8", "public_ipv4": "8.8.8.8",
                       "user": "automation", "port": 22, "machine_id": "a" * 32,
                       "host_keys": ["ssh-ed25519 c3ludGhldGljLXRlc3Qta2V5"]},
    }
    for role, name, address in (("tra", "tra-v07", "10.23.45.10"),
                                ("testserver", "testserver1-v07", "10.23.45.11")):
        result[role] = {
            "vm_name": name, "uuid": "00000000-0000-4000-8000-000000000007",
            "address": address, "user": "automation", "port": 22,
            "machine_id": "b" * 32, "hypervisor_machine_id": "a" * 32, "verified": True,
            "host_keys": ["ssh-ed25519 c3ludGhldGljLXRlc3Qta2V5 synthetic-comment"],
        }
    result["artifacts"] = {
        "schema_version": 1, "counter": number,
        "images": [{"name": name, "archive": f"/opt/aiops-mcp-artifacts/v07/{kind}.tar",
                    "image_id": "sha256:" + "c" * 64, "sha256": "d" * 64, "bytes": 1024}
                   for kind, name in FILTERS.IMAGES.items()],
        "rpms": [{"path": "/opt/aiops-mcp-artifacts/v07/rpms/podman.rpm", "nevra": "synthetic-podman",
                  "sha256": "e" * 64, "bytes": 1024, "signature_verified": True}],
    }
    result["zabbix"] = {"instance_name": "aap27-test-7", "instance_number": number,
                        "vm_name": "zabbix-v07", "hypervisor_machine_id": "a" * 32,
                        "address": "10.23.45.12", "api_url": "http://10.23.45.12/api_jsonrpc.php"}
    return result


class MCPDeploymentTests(unittest.TestCase):
    def test_verified_guests_and_local_artifacts_are_selected(self):
        config = FILTERS.configuration(deployment())
        self.assertEqual(config["tra"]["vm_name"], "tra-v07")
        self.assertEqual(config["testserver"]["host_keys"], ["ssh-ed25519 c3ludGhldGljLXRlc3Qta2V5"])
        self.assertGreaterEqual(config["artifacts"]["minimum_free_bytes"], 2 * 1024 ** 3)

    def test_foreign_unverified_or_public_guest_is_rejected(self):
        for field, value in (("vm_name", "tra-v08"), ("verified", False),
                             ("hypervisor_machine_id", "c" * 32), ("address", "8.8.8.8"),
                             ("machine_id", ""), ("host_keys", []), ("user", "root")):
            data = deployment()
            data["tra"][field] = value
            with self.subTest(field=field), self.assertRaises(AnsibleFilterError):
                FILTERS.configuration(data)

    def test_foreign_paths_unsigned_rpms_and_missing_images_are_rejected(self):
        variants = []
        for field, value in (("counter", 8), ("images", [])):
            data = deployment()
            data["artifacts"][field] = value
            variants.append(data)
        for field, value in (("signature_verified", False), ("path", "/tmp/unreviewed.rpm"),
                             ("path", "/opt/aiops-mcp-artifacts/v07/rpms/../unreviewed.rpm")):
            data = deployment()
            data["artifacts"]["rpms"][0][field] = value
            variants.append(data)
        data = deployment()
        data["artifacts"]["images"][0]["archive"] = "/opt/aiops-mcp-artifacts/v08/linux-mcp.tar"
        variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(AnsibleFilterError):
                FILTERS.configuration(data)

    def test_existing_client_entries_are_preserved(self):
        existing = {"unrelated": {"setting": True}, "projects": {"/home/automation/claude-wd": {
            "mcpServers": {"existing": {"command": "preserve"}}, "trust_setting": "preserve"}}}
        result = FILTERS.client_configuration(json.dumps(existing), "/home/automation/claude-wd",
                                              "linux-mcp", {"command": "podman"})
        self.assertEqual(result["unrelated"], existing["unrelated"])
        self.assertEqual(result["projects"]["/home/automation/claude-wd"]["mcpServers"]["existing"],
                         {"command": "preserve"})
        self.assertEqual(result["projects"]["/home/automation/claude-wd"]["trust_setting"], "preserve")

    def test_zabbix_mcp_requires_the_matching_new_private_api(self):
        data = deployment()
        result = FILTERS.zabbix_configuration(data, "synthetic-new-target-only-token")
        self.assertEqual(result["origin"], "http://10.23.45.12")
        for field, value in (("instance_number", 8), ("hypervisor_machine_id", "c" * 32),
                             ("api_url", "https://production.example.com/api_jsonrpc.php")):
            changed = copy.deepcopy(data)
            changed["zabbix"][field] = value
            with self.subTest(field=field), self.assertRaises(AnsibleFilterError):
                FILTERS.zabbix_configuration(changed, "synthetic-new-target-only-token")
        with self.assertRaises(AnsibleFilterError):
            FILTERS.zabbix_configuration(data, "")


class StdioVerificationTests(unittest.TestCase):
    def fake_server(self, root, hostname="testserver1-v07", extra_tools=None, tool_error=False):
        path = root / "fake_mcp.py"
        path.write_text(
            "import json,sys\n"
            "for line in sys.stdin:\n"
            " request=json.loads(line); method=request['method']; response={}\n"
            " if method=='notifications/initialized': continue\n"
            " if method=='initialize': response={'protocolVersion':'2024-11-05','serverInfo':{'name':'synthetic','version':'1'}}\n"
            " elif method=='tools/list': response={'tools':[{'name':n} for n in "
            + repr(["get_system_information", "host_get"] + (extra_tools or [])) + "]}\n"
            " elif method=='tools/call': response="
            + repr({"isError": tool_error, "structuredContent": {
                "hostname": hostname, "result": VERIFIER.ZABBIX_DATA_PREFIX + "1"}, "content": []}) + "\n"
            " print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':response}),flush=True)\n"
        )
        return [sys.executable, str(path)]

    def check(self, **options):
        with tempfile.TemporaryDirectory(prefix="mcp-protocol-test-") as temporary:
            server = options.pop("server", "linux-mcp")
            result = VERIFIER.verify(self.fake_server(Path(temporary), **options), server,
                                     expected_hostname="testserver1-v07", timeout=5)
            if not result["verification_passed"]:
                diagnostic = Path(result["diagnostic_file"])
                self.assertEqual(diagnostic.stat().st_mode & 0o777, 0o600)
                diagnostic.unlink()
            return result

    def test_real_stdio_protocol_checks_the_expected_linux_host(self):
        self.assertTrue(self.check()["verification_passed"])

    def test_unexpected_host_or_script_toolset_fails(self):
        self.assertFalse(self.check(hostname="unexpected-host")["verification_passed"])
        self.assertFalse(self.check(extra_tools=["run_script"])["verification_passed"])

    def test_zabbix_readonly_query_must_succeed(self):
        self.assertTrue(self.check(server="zabbix")["verification_passed"])
        self.assertFalse(self.check(server="zabbix", tool_error=True)["verification_passed"])


if __name__ == "__main__":
    unittest.main()
