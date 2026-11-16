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
from ansible.errors import AnsibleFilterError
from ansible.utils.unsafe_proxy import wrap_var
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, is_trusted_as_template

from test_zabbix_native_firewall import inputs, policy

ROOT = Path(__file__).resolve().parents[1]


def release_inputs(app_grant=True):
    values=inputs(); deployment=values['demo_zabbix_deployment']
    server=deployment['testserver']
    server.update(disk='/opt/vms/testserver1-v07.disk.qcow2',network='isolated',bridge='demo0',mac='52:54:00:00:00:31')
    tra=copy.deepcopy(server)
    tra.update(vm_name='tra-v07',disk='/opt/vms/tra-v07.disk.qcow2',address='192.0.2.125',
        uuid='33333333-3333-3333-3333-333333333333',machine_id='3'*32,mac='52:54:00:00:00:32',
        host_keys=['ssh-ed25519 QkJCQg=='])
    mcp=copy.deepcopy(deployment);mcp['tra']=tra
    base={'bridge':'demo0','ipv4':'192.0.2.123','mac':'52:54:00:00:00:30'}
    released=[base]+[{'bridge':guest['bridge'],'ipv4':guest['address'],'mac':guest['mac']} for guest in (server,tra)]
    projection=deployment['isolation_policy'];projection['released_clients']=released
    projection['protected_ipv4']=['198.51.100.20']
    if not app_grant:projection['guest_host_clients']=projection['guest_host_clients'][:1]
    config=policy.configuration(deployment);values['demo_zabbix_config']=config
    checked=copy.deepcopy(projection)
    if app_grant:checked['guest_host_clients']=checked['guest_host_clients'][:1]
    current=copy.deepcopy(checked);current['released_clients']=[base]
    pin=config['hypervisor']
    variables={'ansible_host':pin['address'],'public_ipv4':pin['public_ipv4'],'ansible_user':pin['user'],
        'ansible_port':pin['port'],'machine_id':pin['machine_id'],'host_keys':pin['host_keys'],
        'isolation_policy':current,'hactar_isolation_policy':copy.deepcopy(current),
        'operator_note':'{{ retain_literal }}'}
    source={'id':302,'inventory':config['cac_import']['inventory_id'],'name':pin['name'],'enabled':True,
        'variables':json.dumps(variables)}
    workload={'id':401,'inventory':201,'name':'localhost','variables':json.dumps({
        'demo_zabbix_deployment':deployment})}
    tra_workload={'id':403,'inventory':201,'name':'tra','variables':json.dumps({
        'demo_mcp_deployment':mcp,'demo_managed_guest':tra,'ansible_host':tra['address'],
        'ansible_user':tra['user'],'ansible_port':tra['port'],'demo_instance_name':config['instance_name'],
        'demo_instance_number':config['instance_number'],'hypervisor_host':pin['name']})}
    values.update(demo_zabbix_firewall_previous_policy=checked)
    proof={'checked_policy':checked,'appliance':values['demo_zabbix_deployment']['firewall']['guest'],
        'inventory':201,'name':'localhost','workload':workload,'tra_workload':tra_workload}
    return values,source,workload,proof


class ZabbixCaCTests(unittest.TestCase):
    def test_native_lookup_variables_preserve_literals_and_reject_conflicting_ownership(self):
        values = inputs()
        config = values['demo_zabbix_config']
        resource = values['demo_zabbix_deployment']['firewall']['guest']
        source = {'vm_resource': resource, 'operator_note': '{{ retain_literal }}'}
        rows = wrap_var([{'inventory': config['cac_import']['inventory_id'],
                          'name': config['vm_name'], 'variables': json.dumps(source)}])
        self.assertFalse(is_trusted_as_template(rows[0]['variables']))
        result = policy.source_inventory_variables(config, resource, rows)
        self.assertEqual(result['operator_note'], '{{ retain_literal }}')
        self.assertFalse(is_trusted_as_template(result['operator_note']))
        self.assertEqual(Templar(loader=DataLoader(),variables={'retain_literal':'must-not-render'}).template(
            result['operator_note']), '{{ retain_literal }}')
        source['vm_resource'] = dict(resource, uuid='33333333-3333-3333-3333-333333333333')
        rows[0]['variables'] = wrap_var(json.dumps(source))
        with self.assertRaisesRegex(AnsibleFilterError, 'ownership conflicts'):
            policy.source_inventory_variables(config, resource, rows)

    def run_case(self, *, failed_import=False, wrong_owner=False, reconcile=False, fault=None, app_grant=True):
        with tempfile.TemporaryDirectory(prefix='zabbix-cac-fixture-') as temporary:
            folder = Path(temporary)
            values = inputs()
            if reconcile:
                values,policy_host,workload,proof=release_inputs(app_grant)
                if reconcile=='server_only':
                    values['demo_zabbix_deployment']['isolation_policy']['released_clients'].pop()
                    values['demo_zabbix_firewall_previous_policy']['released_clients'].pop()
                    saved_workload=json.loads(workload['variables'])
                    saved_workload['demo_zabbix_deployment']=copy.deepcopy(values['demo_zabbix_deployment'])
                    workload['variables']=json.dumps(saved_workload)
                if fault in ('uuid','mac','counter','foreign'):
                    saved_tra=json.loads(proof['tra_workload']['variables'])
                    role=saved_tra['demo_managed_guest']
                    if fault=='uuid':role['uuid']='44444444-4444-4444-4444-444444444444'
                    elif fault=='mac':role['mac']='52:54:00:00:00:99'
                    elif fault=='counter':saved_tra['demo_instance_number']=8
                    else:role['hypervisor_machine_id']='9'*32
                    proof['tra_workload']['variables']=json.dumps(saved_tra)
                if fault=='unknown':
                    values['demo_zabbix_deployment']['isolation_policy']['released_clients'].append(
                        {'bridge':'demo0','ipv4':'192.0.2.126','mac':'52:54:00:00:00:33'})
                    values['demo_zabbix_firewall_previous_policy']['released_clients'].append(
                        {'bridge':'demo0','ipv4':'192.0.2.126','mac':'52:54:00:00:00:33'})
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
            current = [{'id': 300, 'name': 'existing-source-anchor', 'inventory': group['inventory'],
                        'variables': json.dumps({'operator_note': '{{ retain_literal }}'})}]
            if reconcile:
                if reconcile=='current':
                    prior=json.loads(policy_host['variables'])
                    for key in ('isolation_policy','hactar_isolation_policy'):
                        prior[key]['released_clients']=copy.deepcopy(deployment['isolation_policy']['released_clients'])
                    policy_host['variables']=json.dumps(prior)
                if fault=='production':
                    altered=json.loads(policy_host['variables'])
                    altered['isolation_policy']['protected_ipv4']=['198.51.100.99']
                    policy_host['variables']=json.dumps(altered)
                current.append(policy_host)
            if wrong_owner:
                resource = copy.deepcopy(values['demo_zabbix_deployment']['firewall']['guest'])
                resource['uuid'] = '22222222-2222-2222-2222-222222222222'
                current.append({'id': 301, 'name': config['vm_name'], 'inventory': group['inventory'],
                                'variables': json.dumps({'vm_resource': resource})})
            state = {'origin': config['cac_import']['controller_host'], 'token': token, 'importer': importer,
                'survey': {'spec': [{'variable': 'aap_instance_key', 'required': True, 'type': 'text'},
                    {'variable': 'debug_logging', 'required': False, 'type': 'multiplechoice',
                     'choices': 'false\ntrue', 'default': 'false'}]},
                'source_hosts': current, 'group': group, 'group_members': ['another-guest'],
                'calls': [], 'failed_import': failed_import,
                'refreshed_host': {'id': 401, 'inventory': 201,
                    'variables': json.dumps({'demo_zabbix_deployment': deployment})},
                'refreshed_template': {'id': 202, 'inventory': 201, 'playbook': 'playbooks/deploy_zabbix_demo.yml',
                    'extra_vars': json.dumps({'demo_runtime_settings_vault': new_cipher})}}
            if reconcile:
                state.update(policy_host_name=config['hypervisor']['name'],policy_host_id=302,workload_host=workload,
                    policy_fault=fault,policy_reads=0,tra_host=proof['tra_workload'])
            state_file = folder / 'controller-fixture.json'
            state_file.write_text(json.dumps(state)); state_file.chmod(0o600)
            collection = folder / 'collections/ansible_collections/ansible/controller/plugins'
            (collection / 'lookup').mkdir(parents=True)
            (collection / 'modules').mkdir()
            lookup = '''from ansible.plugins.lookup import LookupBase
from ansible.utils.unsafe_proxy import wrap_var
from pathlib import Path
import json
class LookupModule(LookupBase):
 def run(self, terms, variables=None, **kwargs):
  state=json.loads(Path(STATE).read_text())
  assert kwargs['host']==state['origin'] and kwargs['oauth_token']==state['token'] and kwargs['verify_ssl'] is True
  endpoint=terms[0].rstrip('/'); query=kwargs.get('query_params',{})
  if endpoint.endswith('/survey_spec'): return [state['survey']]
  if endpoint=='job_templates/'+str(state['importer']['id']): return [state['importer']]
  if endpoint=='job_templates/202': return [state['refreshed_template']]
  if endpoint.startswith('groups/'): return [state['group']]
  if endpoint.startswith('hosts/'):
   if state.get('policy_fault')=='read_denied': raise AssertionError('Synthetic read permission denial')
   row=next(row for row in state['source_hosts'] if row['id']==int(endpoint.split('/')[1]))
   state['policy_reads']=state.get('policy_reads',0)+1
   if state.get('policy_fault')=='race' and state['policy_reads']==1:
    values=json.loads(row['variables']);values['operator_note']='concurrent';row['variables']=json.dumps(values)
   if state.get('policy_fault')=='readback' and state['policy_reads']==2: row['variables']='{}'
   Path(STATE).write_text(json.dumps(state))
   return wrap_var([row])
  if endpoint=='hosts' and query['inventory']==201:
   if query.get('name')=='tra':
    state['tra_reads']=state.get('tra_reads',0)+1;Path(STATE).write_text(json.dumps(state))
    return wrap_var([state['tra_host']])
   return wrap_var([state['workload_host'] if state.get('workload_host') and 'job_launch' not in state['calls'] else state['refreshed_host']])
  if endpoint=='hosts':
   rows=state['source_hosts']
   if 'name' in query: rows=[row for row in rows if row['name']==query['name']]
   return wrap_var(rows)
  raise AssertionError(endpoint)
'''.replace('STATE', repr(str(state_file)))
            (collection / 'lookup/controller_api.py').write_text(lookup)
            module = '''from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import json
spec={'controller_host':{},'controller_oauthtoken':{'no_log':True},'validate_certs':{'type':'bool'},
 'max_retries':{'type':'int'},'inventory':{},'name':{},'variables':{'type':'dict'},'state':{},'enabled':{'type':'bool'},
 'hosts':{'type':'list'},'preserve_existing_hosts':{'type':'bool'},'job_template':{},'extra_vars':{'type':'dict'},
 'wait':{'type':'bool'},'interval':{'type':'int'},'timeout':{'type':'int'}}
m=AnsibleModule(argument_spec=spec)
p=m.params; path=Path(STATE); s=json.loads(path.read_text())
assert p['controller_host']==s['origin'] and p['controller_oauthtoken']==s['token'] and p['validate_certs'] is True
assert p['max_retries']==0
operation=OPERATION
if operation=='host' and p['name']==s.get('policy_host_name'):
 s['calls'].append('policy_host')
 if s.get('policy_fault')=='write_denied':
  path.write_text(json.dumps(s));m.fail_json(msg='Synthetic write permission denial')
 assert p['enabled'] is True
 target=next(row for row in s['source_hosts'] if row['name']==p['name'])
 target['variables']=json.dumps(p['variables'])
 path.write_text(json.dumps(s));m.exit_json(changed=True,id=target['id'])
s['calls'].append(operation)
if operation=='host':
 assert p['enabled'] is False
 assert not any(key in p['variables'] for key in ('ansible_host','ansible_user','ansible_port','host_keys','machine_id'))
 existing=[row for row in s['source_hosts'] if row['name']!=p['name']]
 updated={'id':301,'inventory':int(p['inventory']),'name':p['name'],'variables':json.dumps(p['variables'])}
 s['source_hosts']=existing+[updated]
elif operation=='group':
 assert p['preserve_existing_hosts'] is True
 s['group_members']+=p['hosts']
else:
 assert p['wait'] is True and p['timeout']==900 and p['interval']==5
 assert int(p['job_template'])==s['importer']['id'] and p['extra_vars']['aap_instance_key']=='aap27-v07'
 choice=next(item for item in s['survey']['spec'] if item['variable']=='debug_logging')
 assert type(p['extra_vars']['debug_logging']) is str
 assert p['extra_vars']['debug_logging'] in choice['choices'].splitlines()
 assert p['extra_vars']['debug_logging']==choice['default']
 if s.get('policy_host_id'):
  source=next(row for row in s['source_hosts'] if row['id']==s['policy_host_id'])
  policy=json.loads(source['variables'])['isolation_policy']
  projected=json.loads(s['refreshed_host']['variables'])['demo_zabbix_deployment']['isolation_policy']
  assert policy['released_clients']==projected['released_clients']
  assert len(policy['guest_host_clients'])==1
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
        self.assertEqual(json.loads(state['source_hosts'][0]['variables']), {'operator_note': '{{ retain_literal }}'})
        self.assertEqual(json.loads(state['source_hosts'][1]['variables'])['vm_resource']['gateway'], '192.168.70.1')

    def test_failed_import_stops_before_refreshed_configuration(self):
        result, state = self.run_case(failed_import=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(state['calls'], ['host', 'group', 'job_launch'])

    def test_conflicting_owner_stops_before_any_source_write_or_import(self):
        result, state = self.run_case(wrong_owner=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(state['calls'], [])


    def test_selected_role_omissions_are_persisted_before_import_and_application_grant_stays_separate(self):
        for app_grant in (True,False):
            with self.subTest(app_grant=app_grant):
                result,state=self.run_case(reconcile=True,app_grant=app_grant)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(state['calls'],['policy_host','host','group','job_launch'])
                row=next(row for row in state['source_hosts'] if row['id']==302)
                variables=json.loads(row['variables'])
                self.assertEqual(len(variables['isolation_policy']['released_clients']),3)
                self.assertEqual(len(variables['isolation_policy']['guest_host_clients']),1)
                self.assertEqual(variables['operator_note'],'{{ retain_literal }}')

    def test_current_source_policy_needs_no_patch_or_optional_tra_proof(self):
        result,state=self.run_case(reconcile='current')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(state['calls'],['host','group','job_launch'])

    def test_testserver_only_omission_does_not_read_optional_tra(self):
        result,state=self.run_case(reconcile='server_only')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(state.get('tra_reads',0),0)
        self.assertEqual(state['calls'],['policy_host','host','group','job_launch'])

    def test_unproved_policy_and_api_failures_prevent_child_import(self):
        for fault in ('unknown','uuid','mac','counter','foreign','production','race','read_denied','readback','write_denied'):
            with self.subTest(fault=fault):
                result,state=self.run_case(reconcile=True,fault=fault)
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
                self.assertNotIn('job_launch',state['calls'])
                self.assertEqual(state['calls'],['policy_host'] if fault in ('readback','write_denied') else [])


class SourcePolicyPlannerTests(unittest.TestCase):
    def setUp(self):
        self.values,self.source,self.workload,self.proof=release_inputs()

    def plan(self,proof=None):
        return policy.source_policy_plan(self.values['demo_zabbix_config'],self.values['demo_zabbix_deployment'],
            [self.source],self.proof if proof is None else proof)

    def test_exact_two_role_repair_is_pure_and_idempotent(self):
        original=copy.deepcopy((self.values,self.source,self.workload,self.proof))
        planned=self.plan();self.assertTrue(planned['changed'])
        self.assertTrue(policy.source_policy_matches(planned,self.source))
        self.assertEqual((self.values,self.source,self.workload,self.proof),original)
        self.source['variables']=json.dumps(planned['variables'])
        self.assertTrue(policy.source_policy_matches(planned,self.source,True))
        minimal={'checked_policy':self.proof['checked_policy'],'appliance':self.proof['appliance']}
        self.assertFalse(self.plan(minimal)['changed'])

    def test_testserver_only_repair_does_not_require_tra_evidence(self):
        self.values['demo_zabbix_deployment']['isolation_policy']['released_clients'].pop()
        self.proof['checked_policy']['released_clients'].pop()
        saved=json.loads(self.proof['workload']['variables'])
        saved['demo_zabbix_deployment']=copy.deepcopy(self.values['demo_zabbix_deployment'])
        self.proof['workload']['variables']=json.dumps(saved)
        self.proof.pop('tra_workload')
        self.assertTrue(self.plan()['changed'])

    def test_tra_saved_record_identity_and_flat_binding_must_match(self):
        for field,value in (('id',0),('inventory',999),('name','foreign')):
            with self.subTest(field=field):
                self.setUp();self.proof['tra_workload'][field]=value
                with self.assertRaises(AnsibleFilterError):self.plan()
        for field,value in (('ansible_host','192.0.2.199'),('ansible_user','foreign'),('ansible_port',2223),
                            ('demo_instance_name','aap27-test-8'),('demo_instance_number',8),('hypervisor_host','foreign')):
            with self.subTest(field=field):
                self.setUp();saved=json.loads(self.proof['tra_workload']['variables'])
                saved[field]=value;self.proof['tra_workload']['variables']=json.dumps(saved)
                with self.assertRaises(AnsibleFilterError):self.plan()

    def test_extra_identity_role_counter_uuid_mac_and_foreign_pin_fail_closed(self):
        for case in ('unknown','wrong_role','counter','uuid','mac','hypervisor','duplicate','missing_proof',
                     'production','other_grant','reordered','native_unchecked','source_pin'):
            with self.subTest(case=case):
                self.setUp(); values=self.values;proof=self.proof
                if case=='unknown':
                    extra={'bridge':'demo0','ipv4':'192.0.2.126','mac':'52:54:00:00:00:33'}
                    values['demo_zabbix_deployment']['isolation_policy']['released_clients'].append(extra)
                    proof['checked_policy']['released_clients'].append(copy.deepcopy(extra))
                    saved=json.loads(proof['workload']['variables']);saved['demo_zabbix_deployment']=copy.deepcopy(values['demo_zabbix_deployment'])
                    proof['workload']['variables']=json.dumps(saved)
                elif case in ('wrong_role','counter','uuid','mac','hypervisor','duplicate'):
                    saved_tra=json.loads(proof['tra_workload']['variables'])
                    role=saved_tra['demo_managed_guest']
                    if case=='wrong_role':role['vm_name']='other-v07'
                    elif case=='counter':saved_tra['demo_instance_number']=8
                    elif case=='uuid':role['uuid']='44444444-4444-4444-4444-444444444444'
                    elif case=='mac':role['mac']='52:54:00:00:00:99'
                    elif case=='hypervisor':role['hypervisor_machine_id']='9'*32
                    else:role['uuid']=saved_tra['demo_mcp_deployment']['testserver']['uuid']
                    proof['tra_workload']['variables']=json.dumps(saved_tra)
                elif case=='missing_proof':proof.pop('checked_policy')
                elif case=='native_unchecked':proof['checked_policy']={}
                else:
                    current=json.loads(self.source['variables'])
                    if case=='production':current['isolation_policy']['protected_ipv4']=['198.51.100.99']
                    elif case=='other_grant':current['isolation_policy']['guest_host_clients'].append({'foreign':True})
                    elif case=='source_pin':current['machine_id']='9'*32
                    else:
                        current['isolation_policy']['released_clients']=list(reversed(values['demo_zabbix_deployment']['isolation_policy']['released_clients'][:2]))
                    self.source['variables']=json.dumps(current)
                with self.assertRaises((AnsibleFilterError,ValueError,KeyError)):self.plan()

    def test_pending_and_already_applied_exact_own_grant_leave_base_alias_unchanged(self):
        for applied in (True,False):
            with self.subTest(applied=applied):
                self.setUp()
                if applied:self.proof['checked_policy']=copy.deepcopy(self.values['demo_zabbix_deployment']['isolation_policy'])
                planned=self.plan()
                self.assertEqual(planned['variables']['isolation_policy']['guest_host_clients'],
                    json.loads(self.source['variables'])['isolation_policy']['guest_host_clients'])
        self.setUp()
        self.values['demo_zabbix_deployment']['isolation_policy']['guest_host_clients'].append({'unproved_app':True})
        with self.assertRaises(AnsibleFilterError):self.plan()
        self.setUp()
        variables=json.loads(self.source['variables'])
        variables['isolation_policy']['guest_host_clients']=copy.deepcopy(
            self.values['demo_zabbix_deployment']['isolation_policy']['guest_host_clients'])
        self.source['variables']=json.dumps(variables)
        with self.assertRaises(AnsibleFilterError):self.plan()

    def test_exact_workload_and_full_preimage_identity_must_match(self):
        for field in ('id','inventory','name'):
            with self.subTest(field=field):
                self.setUp();self.proof['workload'][field]=0 if field!='name' else 'foreign'
                with self.assertRaises(AnsibleFilterError):self.plan()
        self.setUp();planned=self.plan()
        for field in ('id','inventory','name','enabled','variables'):
            row=copy.deepcopy(self.source)
            row[field]='{}' if field=='variables' else ('foreign' if field=='name' else 0)
            self.assertFalse(policy.source_policy_matches(planned,row))


if __name__ == '__main__':
    unittest.main()
