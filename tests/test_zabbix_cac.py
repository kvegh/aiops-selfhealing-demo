"""Exercise the real Ansible sequence with disposable Controller API fixtures.

The collection fixtures record calls; they do not emulate or certify AAP.
Actual collection resolution and live acceptance are separate checks.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

from test_zabbix_native_firewall import inputs

ROOT = Path(__file__).resolve().parents[1]


class ZabbixCaCTests(unittest.TestCase):
    def run_case(self, *, failed_import=False, wrong_owner=False):
        with tempfile.TemporaryDirectory(prefix='zabbix-cac-fixture-') as temporary:
            folder = Path(temporary)
            values = inputs()
            config = values['demo_zabbix_config']
            deployment = copy.deepcopy(values['demo_zabbix_deployment'])
            deployment['cac_import'] = config['cac_import']
            values.update(awx_inventory_id=201, awx_job_template_id=202,
                demo_zabbix_firewall_workspace={'path': str(folder)},
                demo_zabbix_firewall_expected_policy={'guest_host_clients': []},
                hactar_isolation_policy={'guest_host_clients': []})
            cert = folder / 'ca.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-subj', '/CN=synthetic-fixture', '-keyout', str(folder / 'key'), '-out', str(cert), '-days', '1'],
                check=True, capture_output=True, timeout=15)
            token = 'synthetic-api-bearer-canary'
            values['demo_aap_mcp'] = {'instance_name': config['instance_name'],
                'url': 'https://192.168.70.10:8448/mcp', 'token': token, 'ca_pem': cert.read_text()}
            vault = VaultLib([('default', VaultSecret(b'synthetic-runtime-password'))])
            def ciphertext(reader):
                return vault.encrypt(yaml.safe_dump({'schema_version': 1,
                    'instances': {config['instance_name']: {'hactar_source_git_token': reader}}}).encode()).decode()
            old_cipher, new_cipher = ciphertext('old-reader-canary'), ciphertext('new-reader-canary')
            group = {'id': config['cac_import']['group_id'], 'inventory': config['cac_import']['inventory_id'],
                'name': 'existing-placement', 'variables': json.dumps({'hypervisor_host': config['hypervisor']['name']})}
            importer = {'id': config['cac_import']['job_template_id'], 'inventory': config['cac_import']['inventory_id'],
                'playbook': 'deploy-cac-project.yml', 'survey_enabled': True,
                'extra_vars': json.dumps({'aap_cac_project_id': 'aiops-selfhealing-demo'})}
            current = []
            if wrong_owner:
                resource = copy.deepcopy(values['demo_zabbix_deployment']['firewall']['guest'])
                resource['uuid'] = '22222222-2222-2222-2222-222222222222'
                current = [{'id': 301, 'name': config['vm_name'], 'inventory': group['inventory'],
                            'variables': json.dumps({'vm_resource': resource})}]
            state = {'origin': config['cac_import']['controller_host'], 'token': token, 'importer': importer,
                'source_hosts': current, 'group': group, 'group_members': ['another-guest'],
                'calls': [], 'failed_import': failed_import,
                'refreshed_host': {'id': 401, 'inventory': 201,
                    'variables': json.dumps({'demo_zabbix_deployment': deployment})},
                'refreshed_template': {'id': 202, 'inventory': 201, 'playbook': 'playbooks/deploy_zabbix_demo.yml',
                    'extra_vars': json.dumps({'demo_runtime_settings_vault': new_cipher})}}
            state_file = folder / 'controller-fixture.json'
            state_file.write_text(json.dumps(state)); state_file.chmod(0o600)
            collection = folder / 'collections/ansible_collections/ansible/controller/plugins'
            (collection / 'lookup').mkdir(parents=True)
            (collection / 'modules').mkdir()
            lookup = '''from ansible.plugins.lookup import LookupBase
from pathlib import Path
import json
class LookupModule(LookupBase):
 def run(self, terms, variables=None, **kwargs):
  state=json.loads(Path(STATE).read_text())
  assert kwargs['host']==state['origin'] and kwargs['oauth_token']==state['token'] and kwargs['verify_ssl'] is True
  endpoint=terms[0].rstrip('/'); query=kwargs.get('query_params',{})
  if endpoint.endswith('/survey_spec'): return [{'spec':[{'variable':'aap_instance_key','required':True}]}]
  if endpoint=='job_templates/'+str(state['importer']['id']): return [state['importer']]
  if endpoint=='job_templates/202': return [state['refreshed_template']]
  if endpoint.startswith('groups/'): return [state['group']]
  if endpoint=='hosts' and query['inventory']==201: return [state['refreshed_host']]
  if endpoint=='hosts': return state['source_hosts']
  raise AssertionError(endpoint)
'''.replace('STATE', repr(str(state_file)))
            (collection / 'lookup/controller_api.py').write_text(lookup)
            module = '''from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import json
spec={'controller_host':{},'controller_oauthtoken':{'no_log':True},'validate_certs':{'type':'bool'},
 'max_retries':{'type':'int'},'inventory':{},'name':{},'variables':{'type':'dict'},'state':{},
 'hosts':{'type':'list'},'preserve_existing_hosts':{'type':'bool'},'job_template':{},'extra_vars':{'type':'dict'},
 'wait':{'type':'bool'},'interval':{'type':'int'},'timeout':{'type':'int'}}
m=AnsibleModule(argument_spec=spec)
p=m.params; path=Path(STATE); s=json.loads(path.read_text())
assert p['controller_host']==s['origin'] and p['controller_oauthtoken']==s['token'] and p['validate_certs'] is True
assert p['max_retries']==0
operation=OPERATION; s['calls'].append(operation)
if operation=='host':
 s['source_hosts']=[{'id':301,'inventory':int(p['inventory']),'name':p['name'],'variables':json.dumps(p['variables'])}]
elif operation=='group':
 assert p['preserve_existing_hosts'] is True
 s['group_members']+=p['hosts']
else:
 assert p['wait'] is True and p['timeout']==900 and p['interval']==5
 assert int(p['job_template'])==s['importer']['id'] and p['extra_vars']['aap_instance_key']=='aap27-v07'
path.write_text(json.dumps(s))
if operation=='job_launch' and s['failed_import']: m.fail_json(msg='synthetic-import-failure')
m.exit_json(changed=True,id=501,status='successful')
'''.replace('STATE', repr(str(state_file)))
            for name in ('host', 'group', 'job_launch'):
                (collection / ('modules/' + name + '.py')).write_text(module.replace('OPERATION', repr(name)))
            play = folder / 'test.yml'
            play.write_text(yaml.safe_dump([{'name': 'Exercise the native VM-to-CaC sequence',
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'vars': values,
                'tasks': [{'name': 'Publish through existing native interfaces', 'ansible.builtin.include_tasks':
                    str(ROOT / 'playbooks/tasks/demo_zabbix_cac.yml')},
                    {'name': 'Require fresh ciphertext despite original extra-var precedence', 'no_log': True,
                     'ansible.builtin.assert': {'that': ["hactar_source_git_token == 'new-reader-canary'",
                         'demo_zabbix_firewall_expected_policy == demo_zabbix_deployment.isolation_policy',
                         'hactar_isolation_policy == demo_zabbix_deployment.isolation_policy']}}]}], sort_keys=False))
            extra = folder / 'extra.json'; extra.write_text(json.dumps({'demo_runtime_settings_vault': old_cipher})); extra.chmod(0o600)
            password = folder / 'password'; password.write_text('synthetic-runtime-password'); password.chmod(0o600)
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                '--vault-password-file', str(password), '-e', '@' + str(extra), str(play)], capture_output=True, text=True,
                env=dict(os.environ, ANSIBLE_LOCAL_TEMP=str(folder / 'local'), ANSIBLE_REMOTE_TEMP=str(folder / 'remote'),
                    ANSIBLE_FILTER_PLUGINS=str(ROOT / 'playbooks/filter_plugins'),
                    ANSIBLE_COLLECTIONS_PATH=str(folder / 'collections'), ANSIBLE_NOCOLOR='1'), timeout=60)
            self.assertNotIn(token, result.stdout + result.stderr)
            self.assertNotIn(new_cipher, result.stdout + result.stderr)
            self.assertFalse(list(folder.glob('aiops-runtime-vault-*')))
            return result, json.loads(state_file.read_text())

    def test_verified_vm_is_saved_imported_and_reloaded_without_replacing_other_members(self):
        result, state = self.run_case()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(state['calls'], ['host', 'group', 'job_launch'])
        self.assertIn('another-guest', state['group_members'])
        self.assertEqual(json.loads(state['source_hosts'][0]['variables'])['vm_resource']['gateway'], '192.168.70.1')

    def test_failed_import_stops_before_refreshed_configuration(self):
        result, state = self.run_case(failed_import=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(state['calls'], ['host', 'group', 'job_launch'])

    def test_conflicting_owner_stops_before_any_source_write_or_import(self):
        result, state = self.run_case(wrong_owner=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(state['calls'], [])


if __name__ == '__main__':
    unittest.main()
