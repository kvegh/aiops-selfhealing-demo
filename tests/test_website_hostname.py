"""Run the real website check tasks with a local curl recorder, without services."""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from ansible.parsing.vault import VaultLib, VaultSecret
import yaml


ROOT = Path(__file__).resolve().parents[1]


class WebsiteHostnameTests(unittest.TestCase):
    def run_checks(self, inventory_hostname=None, extra_hostname=None):
        with tempfile.TemporaryDirectory(prefix="demo-hostname-") as temporary:
            root = Path(temporary)
            (root / "playbooks").mkdir()
            (root / "bin").mkdir()
            password = b"local-test-password"
            password_file = root / "vault-password"
            password_file.write_bytes(password)
            password_file.chmod(0o600)
            vault = VaultLib([("default", VaultSecret(password))])
            (root / "myvars").write_bytes(vault.encrypt(yaml.safe_dump({
                "vault_demo_website_public_hostname": "production.example.invalid",
            }).encode()))

            plays = []
            for filename, states in (
                ("demo_website.yml", ("enabled", "disabled")),
                ("restore_website_content.yml", (None,)),
                ("arm_demo_button.yml", (None,)),
            ):
                original = yaml.safe_load((ROOT / "playbooks" / filename).read_text())[0]
                for state in states:
                    play = copy.deepcopy(original)
                    play.update(hosts="all", become=False, gather_facts=False)
                    play["tasks"] = [
                        task for task in play["tasks"]
                        if task.get("ansible.builtin.command", {}).get("argv", [None])[0] == "curl"
                    ]
                    if state:
                        play["vars"]["demo_website_state"] = state
                    plays.append(play)
            playbook = root / "playbooks" / "checks.yml"
            playbook.write_text(yaml.safe_dump(plays, sort_keys=False))

            host_vars = {"ansible_connection": "local"}
            if inventory_hostname:
                host_vars["demo_website_public_hostname"] = inventory_hostname
            inventory = root / "inventory.yml"
            inventory.write_text(yaml.safe_dump({"all": {"hosts": {"localhost": host_vars}}}))
            log = root / "curl.jsonl"
            curl = root / "bin" / "curl"
            curl.write_text(
                "#!/usr/bin/python3\n"
                "import json,os,sys\n"
                "with open(os.environ['DEMO_CURL_LOG'], 'a') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "print('200', end='')\n"
            )
            curl.chmod(0o700)
            config = root / "ansible.cfg"
            config.write_text("[defaults]\n")
            env = dict(os.environ, PATH=str(root / "bin") + os.pathsep + os.environ["PATH"],
                       ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(root / "local"),
                       ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                       ANSIBLE_VAULT_PASSWORD_FILE=str(password_file), DEMO_CURL_LOG=str(log),
                       ANSIBLE_NOCOLOR="1")
            command = [shutil.which("ansible-playbook"), "-i", str(inventory), str(playbook)]
            if extra_hostname:
                command.extend(["--extra-vars", json.dumps({"demo_website_public_hostname": extra_hostname})])
            result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(calls), 5)
            hostname = extra_hostname or inventory_hostname or "production.example.invalid"
            for args, path in zip(calls, ("content.html", "index.html", "content.html", "content.html", "armed")):
                self.assertEqual(args, ["-sS", "-o/dev/null", "-w%{http_code}", "--resolve",
                                        f"{hostname}:443:127.0.0.1", f"https://{hostname}/{path}"])

    def test_vault_default_preserves_production_checks(self):
        self.run_checks()

    def test_inventory_selects_independent_test_hostname(self):
        self.run_checks(inventory_hostname="demo.test.example.invalid")

    def test_job_override_takes_precedence_over_inventory(self):
        self.run_checks(inventory_hostname="demo.test.example.invalid",
                        extra_hostname="demo.rehearsal.example.invalid")


if __name__ == "__main__":
    unittest.main()
