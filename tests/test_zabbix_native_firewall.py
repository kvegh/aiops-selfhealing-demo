"""Run the real AIOps orchestration with disposable native/vendor fixtures.

These tests do not run Git, libvirt, nft or firewalld. Hactar owns the actual
native parser/readback tests; this suite verifies its caller and failure bounds.
"""
import copy
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import yaml

from test_versioned_zabbix import deployment, policy

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'playbooks/tasks'


def inputs():
    config = policy.configuration(deployment())
    keys = ['ssh-ed25519 AAAA'] * 3
    record = policy.metadata(config, keys)
    root = ET.Element('domain')
    ET.SubElement(root, 'name').text = config['vm_name']
    ET.SubElement(root, 'uuid').text = '11111111-1111-1111-1111-111111111111'
    ET.SubElement(root, 'description').text = json.dumps(record)
    devices = ET.SubElement(root, 'devices')
    disk = ET.SubElement(devices, 'disk', device='disk')
    ET.SubElement(disk, 'source', file=config['disk'])
    nic = ET.SubElement(devices, 'interface', type='network')
    ET.SubElement(nic, 'source', network='isolated')
    ET.SubElement(nic, 'mac', address='52:54:00:12:34:56')
    xml = ET.tostring(root).decode()
    native = policy.domain_record(xml, config)
    network = {'bridge': 'demo0', 'gateway': '192.168.70.1'}
    guest = policy.provenance(config, native, '192.168.70.10', network, '3' * 32)
    grant = {'bridge': 'demo0', 'ipv4': guest['address'], 'mac': guest['mac'],
             'destinations': [network['gateway']], 'ports': [443]}
    other = {'bridge': 'demo0', 'ipv4': '192.168.70.20', 'mac': '52:54:00:12:34:57',
             'destinations': [network['gateway']], 'ports': [2222]}
    desired = {'bridges': ['demo0'], 'dns_bridges': ['demo0'], 'guest_host_clients': [other, grant]}
    before = dict(desired, guest_host_clients=[other])
    selected = dict(deployment(), isolation_policy=desired, firewall={
        'hactar_source_revision': 'a' * 40, 'protected_production_ipv4': '198.51.100.20', 'guest': guest})
    return {'demo_zabbix_deployment': selected, 'demo_zabbix_config': config,
            'demo_zabbix_network': network, 'demo_zabbix_guest_record': native,
            'demo_zabbix_guest_ip': guest['address'], 'demo_zabbix_guest_machine_id': {'stdout': guest['machine_id']},
            'demo_zabbix_firewall_expected_policy': desired, 'hactar_source_public_ip': '198.51.100.20',
            'ansible_facts': {'all_ipv4_addresses': [network['gateway']]},
            'fixture_xml': xml, 'fixture_applied_policy': before, 'fixture_role_calls': [],
            'fixture_fail_role': False}


class ZabbixNativeFirewallTests(unittest.TestCase):
    def run_source_auth(self, token, repository):
        """Exercise native validation and Git URL scoping without network access."""
        with tempfile.TemporaryDirectory(prefix='aiops-source-auth-test-') as temporary:
            root = Path(temporary)
            prepare = yaml.safe_load((TASKS / 'demo_zabbix_firewall_prepare.yml').read_text())
            checkout = next(task for task in prepare if 'ansible.builtin.git' in task)
            values = inputs()
            if token is not None:
                values['hactar_source_git_token'] = token
            header = 'Authorization: Basic ' + base64.b64encode(('x-access-token:' + (token or '')).encode()).decode()
            tasks = [prepare[0], {
                'name': 'Inspect the native Git URL-scoped authorization without connecting',
                'ansible.builtin.command': {'argv': ['git', 'config', '--get-urlmatch', 'http.extraheader', repository]},
                'environment': checkout['environment'], 'register': 'fixture_git_auth',
                'changed_when': False, 'failed_when': 'fixture_git_auth.rc not in [0, 1]', 'no_log': True,
            }, {
                'name': 'Require authentication only for the exact dependency repository',
                'ansible.builtin.assert': {'that': [
                    'fixture_git_auth.stdout == ' + repr(header if repository.startswith(checkout['ansible.builtin.git']['repo'] + '/') else '')
                ], 'quiet': True}, 'no_log': True,
            }]
            play = root / 'check.yml'
            play.write_text(yaml.safe_dump([{'name': 'Check private source authentication',
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': values, 'tasks': tasks}], sort_keys=False))
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                         ANSIBLE_NOCOLOR='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1'),
                text=True, capture_output=True, timeout=30)
            self.assertNotIn(token or 'synthetic-source-reader', result.stdout + result.stderr)
            self.assertNotIn(header, result.stdout + result.stderr)
            return result

    def test_existing_reader_is_delivered_only_to_the_fixed_git_repository_without_logging(self):
        for repository in ('https://github.com/kvegh/hactarconfig.git/info/refs',
                           'https://github.com/example/unrelated.git/info/refs'):
            result = self.run_source_auth('synthetic-source-reader', repository)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_or_multiline_reader_fails_before_retrieval(self):
        for token in (None, 'synthetic-source-reader\nextra-header'):
            result = self.run_source_auth(token, 'https://github.com/kvegh/hactarconfig.git/info/refs')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def run_case(self, mode='grant', change=None):
        with tempfile.TemporaryDirectory(prefix='aiops-native-firewall-test-') as temporary:
            root = Path(temporary)
            source = root / 'hactar/playbooks/tasks'
            source.mkdir(parents=True)
            # Standard Ansible fixtures replace external Hactar native operations.
            (source / 'replacement-isolation-validate.yml').write_text(yaml.safe_dump([{
                'name': 'Validate complete fixture CaC input', 'ansible.builtin.assert': {
                    'that': ['hactar_isolation_policy is mapping', "hactar_source_public_ip == '198.51.100.20'"]}}]))
            (source / 'replacement-isolation-readback.yml').write_text(yaml.safe_dump([{
                'name': 'Supply exact native state comparison', 'ansible.builtin.set_fact': {
                    '__hactar_isolation_matches': '{{ hactar_isolation_policy == fixture_applied_policy }}'}}]))
            (source / 'replacement-isolation-apply.yml').write_text(yaml.safe_dump([{
                'name': 'Apply only the selected complete fixture CaC policy', 'ansible.builtin.set_fact': {
                    'fixture_applied_policy': '{{ hactar_isolation_policy }}', '__hactar_isolation_matches': True}}]))
            vendor = root / 'collections/ansible_collections/redhat/rhel_system_roles/roles/firewall/tasks'
            vendor.mkdir(parents=True)
            (vendor / 'main.yml').write_text(yaml.safe_dump([
                {'name': 'Retain the exact certified role inputs for inspection', 'ansible.builtin.set_fact': {
                    'fixture_role_calls': '{{ fixture_role_calls + [firewall] }}'}},
                {'name': 'Fail the first fixture operation when requested', 'ansible.builtin.fail': {
                    'msg': 'synthetic-vendor-failure'},
                 'when': 'fixture_fail_role and fixture_role_calls | length == 1'},
            ], sort_keys=False))
            values = inputs()
            values['hactar_firewall_source_root'] = str(root / 'hactar')
            if change:
                change(values)
            lock = root / 'lock'
            artifact = root / 'outcome.json'
            if mode == 'check':
                tasks = yaml.safe_load((TASKS / 'demo_zabbix_firewall_check.yml').read_text())
            else:
                tasks = copy.deepcopy(yaml.safe_load((TASKS / 'demo_zabbix_firewall_grant.yml').read_text()))
                acquire = tasks[0]['block'][0]
                acquire['ansible.builtin.command']['argv'][-1] = str(lock)
                acquire.update(retries=0, delay=0)
                transaction = tasks[1]
                transaction['always'][0]['ansible.builtin.command']['argv'][-1] = str(lock)
                for task in transaction['block']:
                    register = task.get('register')
                    if register == 'demo_zabbix_firewall_machine_id':
                        task.clear()
                        task.update({'name': 'Supply actual hypervisor identity fixture', 'ansible.builtin.set_fact': {
                            'demo_zabbix_firewall_machine_id': {'stdout': '1' * 32}}})
                        # Keep the actual production assertion in the fixture.
                        task['failed_when'] = 'demo_zabbix_firewall_machine_id.stdout | trim != demo_zabbix_config.hypervisor.machine_id'
                    elif register == 'demo_zabbix_firewall_domains':
                        task.clear()
                        task.update({'name': 'Supply both actual guest definition fixtures', 'ansible.builtin.set_fact': {
                            'demo_zabbix_firewall_domains': {'results': [{'stdout': '{{ fixture_xml }}'}, {'stdout': '{{ fixture_xml }}'}]}}})
                    elif register == 'demo_zabbix_firewall_zone':
                        task.clear()
                        task.update({'name': 'Supply verified native zone fixture', 'ansible.builtin.set_fact': {
                            'demo_zabbix_firewall_zone': {'stdout': 'libvirt'}}})
                    elif register == 'demo_zabbix_firewall_previous_rules':
                        task.clear()
                        task.update({'name': 'Supply absent prior exact native rules', 'ansible.builtin.set_fact': {
                            'demo_zabbix_firewall_previous_rules': {'results': [{'rc': 1}, {'rc': 1}]}}})
                    elif 'block' in task:
                        verify = task['block'][-1]
                        verify.clear()
                        verify.update({'name': 'Require the exact ordinary rule to have been requested',
                            'ansible.builtin.assert': {'that': [
                                'fixture_role_calls | length == 1',
                                "fixture_role_calls[0][0].state == 'enabled'",
                                'fixture_role_calls[0][0].runtime and fixture_role_calls[0][0].permanent']}})
                transaction['always'].append({'name': 'Retain safe fixture results', 'ansible.builtin.copy': {
                    'dest': str(artifact), 'content': '{{ {"calls": fixture_role_calls, "policy": fixture_applied_policy} | to_json }}',
                    'mode': '0600'}})
            play = root / 'check.yml'
            play.write_text(yaml.safe_dump([{'name': 'Check bounded monitoring firewall orchestration',
                'hosts': 'localhost', 'connection': 'local', 'become': False, 'gather_facts': False,
                'vars': values, 'tasks': tasks}], sort_keys=False))
            config = root / 'ansible.cfg'
            config.write_text('[defaults]\nfilter_plugins=' + str(ROOT / 'playbooks/filter_plugins') + '\n')
            # Relative task includes in the tested file still resolve to its own source.
            for name in ('demo_zabbix_firewall_check.yml',):
                (root / name).write_text((TASKS / name).read_text())
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                       ANSIBLE_REMOTE_TEMP=str(root / 'remote'), ANSIBLE_COLLECTIONS_PATH=str(root / 'collections'),
                       ANSIBLE_NOCOLOR='1')
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                                    env=env, text=True, capture_output=True, timeout=60)
            output = json.loads(artifact.read_text()) if artifact.exists() else None
            return result, output, lock.exists()

    def test_exact_pending_grant_succeeds_and_preserves_the_other_guest(self):
        result, output, locked = self.run_case()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(locked)
        self.assertEqual(output['policy'], inputs()['demo_zabbix_firewall_expected_policy'])
        rules = output['calls'][0]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['zone'], 'libvirt')
        self.assertIn('source address="192.168.70.10/32"', rules[0]['rich_rule'])
        self.assertIn('destination address="192.168.70.1/32" port port="443"', rules[0]['rich_rule'])

    def test_already_applied_complete_cac_matches_without_a_previous_state_guess(self):
        result, unused, locked = self.run_case(mode='check', change=lambda value: value.update(
            fixture_applied_policy=copy.deepcopy(value['demo_zabbix_firewall_expected_policy'])))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(locked)

    def test_wrong_saved_uuid_and_hypervisor_never_write_permissions_and_release_the_guard(self):
        def wrong_uuid(values):
            values['demo_zabbix_deployment']['firewall']['guest']['uuid'] = '22222222-2222-2222-2222-222222222222'

        def wrong_host(values):
            values['demo_zabbix_config']['hypervisor']['machine_id'] = '4' * 32

        for change in (wrong_uuid, wrong_host):
            with self.subTest(change=change.__name__):
                result, output, locked = self.run_case(change=change)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(locked)
                self.assertEqual(output['calls'], [])

    def test_extra_native_grant_is_not_adopted_as_previous_state(self):
        def extra(values):
            values['fixture_applied_policy'] = copy.deepcopy(values['fixture_applied_policy'])
            values['fixture_applied_policy']['guest_host_clients'].append({
                'bridge': 'demo0', 'ipv4': '192.168.70.30', 'mac': '52:54:00:12:34:58',
                'destinations': ['192.168.70.1'], 'ports': [444]})
        result, output, locked = self.run_case(change=extra)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(locked)
        self.assertEqual(output['calls'], [])

    def test_missing_fresh_instance_owner_never_grants_access(self):
        def missing_owner(values):
            values['demo_zabbix_deployment']['firewall'].pop('guest')
        result, output, locked = self.run_case(change=missing_owner)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(locked)
        self.assertEqual(output['calls'], [])

    def test_failed_vendor_write_restores_only_previous_rule_states_and_policy(self):
        result, output, locked = self.run_case(change=lambda value: value.update(fixture_fail_role=True))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(locked)
        self.assertEqual(output['policy'], inputs()['fixture_applied_policy'])
        self.assertEqual(len(output['calls']), 2)
        self.assertEqual([row['state'] for row in output['calls'][1]], ['disabled', 'disabled'])

    def test_source_pin_and_cleanup_are_explicit_and_no_legacy_execution_remains(self):
        prepare = yaml.safe_load((TASKS / 'demo_zabbix_firewall_prepare.yml').read_text())
        checkout = next(task['ansible.builtin.git'] for task in prepare if 'ansible.builtin.git' in task)
        self.assertEqual(checkout['version'], '{{ demo_zabbix_deployment.firewall.hactar_source_revision }}')
        self.assertFalse(checkout['recursive'])
        play = yaml.safe_load((ROOT / 'playbooks/deploy_zabbix_demo.yml').read_text())[0]
        cleanup = play['tasks'][0]['always']
        self.assertTrue(any(task['ansible.builtin.file']['path'] == '{{ demo_zabbix_firewall_workspace.path }}' for task in cleanup))
        configure = next(task['block'] for task in play['tasks'][0]['block']
                         if task['name'] == "Configure only this instance's monitoring infrastructure")
        include_order = [task['ansible.builtin.include_tasks'] for task in configure if 'ansible.builtin.include_tasks' in task]
        self.assertLess(include_order.index('tasks/demo_zabbix_monitoring.yml'),
                        include_order.index('tasks/demo_zabbix_firewall_grant.yml'))
        self.assertLess(include_order.index('tasks/demo_zabbix_firewall_grant.yml'),
                        include_order.index('tasks/demo_zabbix_finalize.yml'))
        for name in ('deploy_zabbix_demo.yml', 'tasks/demo_zabbix_vm.yml'):
            self.assertNotIn('hactar-recovery-isolation, check', (ROOT / 'playbooks' / name).read_text())
        grant = (TASKS / 'demo_zabbix_firewall_grant.yml').read_text()
        self.assertNotIn('replacement-isolation.json', grant)
        self.assertNotIn('python', grant)

    def test_checkout_and_public_trust_file_are_removed_after_a_downstream_failure(self):
        with tempfile.TemporaryDirectory(prefix='aiops-source-cleanup-test-') as temporary:
            directory = Path(temporary)
            checkout = directory / 'checkout'
            checkout.mkdir()
            (checkout / 'public-source').write_text('synthetic')
            trust = directory / 'known-hosts'
            trust.write_text('synthetic-public-key')
            source = yaml.safe_load((ROOT / 'playbooks/deploy_zabbix_demo.yml').read_text())[0]
            transaction = copy.deepcopy(source['tasks'][0])
            transaction['block'] = [{'name': 'Fail the disposable downstream fixture',
                                     'ansible.builtin.fail': {'msg': 'synthetic-downstream-failure'}}]
            play = directory / 'check.yml'
            play.write_text(yaml.safe_dump([{'name': 'Check source checkout cleanup after failure',
                'hosts': 'localhost', 'connection': 'local', 'become': False, 'gather_facts': False,
                'vars': {'demo_zabbix_firewall_workspace': {'path': str(checkout)},
                         'demo_zabbix_known_hosts': {'path': str(trust)}},
                'tasks': [transaction]}], sort_keys=False))
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                         ANSIBLE_REMOTE_TEMP=str(directory / 'remote'), ANSIBLE_NOCOLOR='1'),
                text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse(checkout.exists())
            self.assertFalse(trust.exists())


if __name__ == '__main__':
    unittest.main()
