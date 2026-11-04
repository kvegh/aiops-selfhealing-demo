"""Exercise the actual webhook value contract and saved remediation condition.

Native Ansible evaluates the shared condition operators here. This is a bounded
contract test, not an EDA activation or a model invocation.
"""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar
import yaml


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "requires existing Node.js")
class AgentEventGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rule = yaml.safe_load(
            (ROOT / "extensions/eda/rulebooks/zabbix-webhook.yml").read_text()
        )[0]["rules"][0]
        cls.script = (ROOT / "playbooks/files/demo-zabbix-event-stream.js").read_text()

    def delivered_event(self, value, name="Zabbix agent is not available"):
        fixture = {
            "endpoint": "https://target.example.invalid/events",
            "username": "synthetic-user", "password": "synthetic-password",
            "event_name": name, "event_id": "7", "trigger_id": "8",
            "host_host": "testserver1-v07",
        }
        if value is not ...:
            fixture["event_value"] = value
        code = """
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));let payload;
global.btoa=value=>Buffer.from(value).toString('base64');
global.HttpRequest=class {
  addHeader() {}
  post(url,body) { payload=JSON.parse(body); }
  getStatus() { return 200; }
};
new Function('value',input.script)(JSON.stringify(input.fixture));
process.stdout.write(JSON.stringify(payload));
"""
        result = subprocess.run(
            ["node", "-e", code],
            input=json.dumps({"script": self.script, "fixture": fixture}),
            text=True, capture_output=True, check=True, timeout=10,
        )
        self.assertNotIn(fixture["password"], result.stdout + result.stderr)
        return {"payload": json.loads(result.stdout)}

    def matches(self, event):
        loader = DataLoader()
        variables = {"event": event}
        conditional = Conditional(loader=loader)
        conditional.when = [self.rule["condition"]]
        return conditional.evaluate_conditional(
            Templar(loader=loader, variables=variables), variables
        )

    def test_problem_macro_strings_and_numbers_deliver_numeric_problem(self):
        for value in (1, "1"):
            with self.subTest(value=value):
                event = self.delivered_event(value)
                self.assertIs(type(event["payload"]["event_value"]), int)
                self.assertTrue(self.matches(event))
        self.assertEqual(
            self.rule["action"]["run_job_template"]["name"],
            "Run Claude to analyse and fix",
        )

    def test_recovery_macro_strings_and_numbers_never_match(self):
        for value in (0, "0"):
            with self.subTest(value=value):
                self.assertFalse(self.matches(self.delivered_event(value)))

    def test_missing_unknown_and_unrelated_events_never_match(self):
        for value in (..., None, "unknown", 2, "2", "", -1):
            with self.subTest(value=value):
                self.assertFalse(self.matches(self.delivered_event(value)))
        for event in ({}, {"payload": {}}, {"payload": {"event_name": "Zabbix agent is not available"}},
                      {"payload": {"event_value": 1}},
                      {"payload": {"event_name": "Zabbix agent is not available", "event_value": "1"}}):
            with self.subTest(event=event):
                self.assertFalse(self.matches(event))
        self.assertFalse(self.matches(self.delivered_event(1, "Demo website content unavailable")))

    def test_existing_case_insensitive_host_specific_agent_name_still_matches(self):
        self.assertTrue(self.matches(self.delivered_event(
            "1", "testserver1-v07: ZABBIX AGENT IS NOT AVAILABLE (for 3m)"
        )))


if __name__ == "__main__":
    unittest.main()
