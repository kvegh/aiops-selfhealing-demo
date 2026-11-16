"""Honor the owner's temporary visible deployment logging direction."""
from pathlib import Path
import unittest
import yaml
ROOT=Path(__file__).resolve().parents[1]


class SubscriptionLoggingTests(unittest.TestCase):
    def test_owned_runtime_tasks_and_blocks_keep_visible_logging(self):
        paths=list((ROOT/'playbooks/tasks').glob('demo_subscription_*.yml'))+[ROOT/'playbooks/tasks/demo_mcp_subscription.yml']
        def check(rows):
            for task in rows:
                self.assertIs(task.get('no_log'),False,task.get('name'))
                for key in ('block','rescue','always'):
                    if key in task:check(task[key])
        for path in paths:
            with self.subTest(path=path.name):check(yaml.safe_load(path.read_text()))
