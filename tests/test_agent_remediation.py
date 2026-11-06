"""Check the selected private MCP, exact repair guard and bounded existing runner."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml
from ansible.errors import AnsibleFilterError

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
F=load('agent_filters','playbooks/filter_plugins/demo_claude.py')
H=load('agent_hook','src/check_demo_tool_request.py')

class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='agent-mcp-ca-');p=Path(cls.temp.name)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(p/'key'),'-out',str(p/'ca'),
                        '-days','1','-subj','/CN=synthetic-test-ca'],capture_output=True,check=True)
        cls.ca=(p/'ca').read_text()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def access(self):
        return {'instance_name':'aap27-test-7','url':'https://192.168.70.10:8448/mcp','ca_pem':self.ca,'token':'synthetic-selected-token'}
    def test_selected_private_metadata_keeps_authentication_in_the_client_file(self):
        access=F.aap_mcp(self.access(),'aap27-test-7')
        self.assertEqual(access['definition']['headers'],{'Authorization':'Bearer synthetic-selected-token'})
        self.assertEqual(access['api_origin'],'https://192.168.70.10')
        old={'theme':'keep','projects':{'/home/synthetic/work':{'mcpServers':{'other':{'keep':True}}}}}
        merged=F.aap_client(json.dumps(old),'/home/synthetic/work',access['definition'])
        self.assertEqual(merged['theme'],'keep');self.assertEqual(merged['projects']['/home/synthetic/work']['mcpServers']['other'],{'keep':True})
        with self.assertRaises(AnsibleFilterError):F.aap_mcp(self.access(),'aap27-test-8')
        for change in [{'url':'https://203.0.113.7:8448/mcp'},{'ca_pem':'invalid'},{'ca_pem':self.ca+'PRIVATE KEY'}]:
            with self.subTest(change=list(change)),self.assertRaises(AnsibleFilterError):F.aap_mcp(dict(self.access(),**change),'aap27-test-7')
        wrong=copy.deepcopy(merged);wrong['projects']['/home/synthetic/work']['mcpServers']['aap-mcp']['url']='https://192.168.70.11:8448/mcp'
        with self.assertRaises(AnsibleFilterError):F.aap_client(json.dumps(wrong),'/home/synthetic/work',access['definition'])
    def test_hook_denies_another_template_overrides_local_or_other_linux_host(self):
        allowed={'tool_name':'mcp__aap-mcp__job_templates_launch_create','tool_input':{'id':'17'}}
        self.assertTrue(H.check(allowed,'17','testserver1'))
        for body in [{'id':'18'},{'id':True},{'id':'017'},{'id':'17','requestBody':{'limit':'other'}},
                     {'id':'17','requestBody':{'extra_vars':{}}},{'id':'17','extra_vars':{}}]:
            with self.subTest(body=body):self.assertFalse(H.check(dict(allowed,tool_input=body),'17','testserver1'))
        for host in [None,'other','192.168.70.20']:
            self.assertFalse(H.check({'tool_name':'mcp__linux-mcp__read_file','tool_input':{'host':host,'path':'/tmp/example'}},'17','testserver1'))
        self.assertTrue(H.check({'tool_name':'mcp__linux-mcp__read_file','tool_input':{'host':'testserver1','path':'/tmp/example'}},'17','testserver1'))
        env=dict(os.environ,AIOPS_ALLOWED_REPAIR_JT_ID='17',AIOPS_ALLOWED_LINUX_HOST='testserver1',AIOPS_ALLOWED_TOOL_NAMES='mcp__aap-mcp__job_templates_launch_create,mcp__linux-mcp__read_file')
        for request,expected in [(allowed,0),(dict(allowed,tool_input={'id':'18'}),2)]:
            result=subprocess.run([sys.executable,str(ROOT/'src/check_demo_tool_request.py')],input=json.dumps(request),env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,expected);self.assertEqual(result.stdout,'')
        invalid=subprocess.run([sys.executable,str(ROOT/'src/check_demo_tool_request.py')],input='{malformed',env=env,capture_output=True,text=True)
        self.assertEqual(invalid.returncode,2)
    def test_saved_repair_drift_is_refused_before_model_or_launch(self):
        row={'id':17,'name':'Deploy Zabbix Agent','playbook':'playbooks/deploy_zabbix_agent.yml','limit':'testserver1',
             'inventory':2,'project':3,**{k:False for k in ['ask_inventory_on_launch','ask_limit_on_launch','ask_variables_on_launch','ask_credential_on_launch']}}
        data={'count':1,'next':None,'results':[row]};self.assertEqual(F.repair_template(data,2,3),17)
        for field,value in [('inventory',9),('project',9),('limit',''),('ask_limit_on_launch',True),('playbook','other.yml')]:
            bad=copy.deepcopy(data);bad['results'][0][field]=value
            with self.subTest(field=field),self.assertRaises(AnsibleFilterError):F.repair_template(bad,2,3)
        target={'vm_name':'testserver1-v07','uuid':'synthetic-uuid','address':'192.168.70.20','mac':'synthetic-mac','machine_id':'b'*32,
                'hypervisor_machine_id':'a'*32,'host_keys':['ssh-ed25519 SYNTHETIC'],'verified':True,'user':'automation','port':22}
        host={'count':1,'next':None,'results':[{'name':'testserver1','variables':json.dumps({'demo_instance_name':'aap27-test-7',
              'ansible_host':target['address'],'ansible_user':target['user'],'ansible_port':target['port'],'demo_managed_guest':target})}]}
        self.assertTrue(F.repair_host(host,target,'aap27-test-7'))
        bad=copy.deepcopy(host);v=json.loads(bad['results'][0]['variables']);v['ansible_host']='192.168.70.99';bad['results'][0]['variables']=json.dumps(v)
        with self.assertRaises(AnsibleFilterError):F.repair_host(bad,target,'aap27-test-7')
    def test_ordered_stream_keeps_phase_findings_and_refuses_incomplete_runs(self):
        messages=[{'type':'assistant','message':{'content':[{'type':'text','text':t}]}} for t in ['Phase1 findings','Phase2 findings','Incident report']]
        terminal={'type':'result','subtype':'success','is_error':False}
        self.assertEqual(F.agent_report('\n'.join(json.dumps(x) for x in messages+[terminal])),['Phase1 findings','Phase2 findings','Incident report'])
        for events in [messages,messages+[dict(terminal,subtype='error_max_turns',is_error=True)]]:
            with self.assertRaises(AnsibleFilterError):F.agent_report('\n'.join(json.dumps(x) for x in events))
    def test_native_runner_arguments_never_include_the_token_or_permission_bypass(self):
        play=yaml.safe_load((ROOT/'playbooks/run_claude_analyse_fix.yml').read_text())[0]
        tasks=play['tasks'][0]['block'];run=next(t for t in tasks if t['name']=='Run the bounded agent with native permissions')
        text=str(run)
        self.assertNotIn('dangerously-skip-permissions',text);self.assertIn('--max-turns',text);self.assertIn('--strict-mcp-config',text)
        self.assertNotIn('demo_aap_mcp.token',text);self.assertNotIn('Authorization',text)
        self.assertIn('NODE_EXTRA_CA_CERTS',run['environment']);self.assertEqual(run['timeout'],630)
        hook=next(t for t in tasks if t['name']=='Add the deny-only hook without editing saved settings')
        self.assertNotIn('permissionDecision',str(hook));self.assertIn('PreToolUse',str(hook))

class NativeRecoveryTests(unittest.TestCase):
    def test_actual_postchecks_reject_failed_child_and_stale_monitoring_despite_success_text(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        import threading,ssl
        state={}
        host={'hostid':'31','host':'testserver1-v07','status':'0',
              'items':[{'key_':'agent.ping','lastclock':'1001','lastvalue':'1','state':'0','status':'0'}],
              'triggers':[{'triggerid':'41','description':'Zabbix agent is not available','value':'0','status':'0'}]}
        class API(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,value):
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(value).encode())
            def do_GET(self):
                if 'id=52' in self.path:
                    self.reply({'count':1,'next':None,'results':[{'id':52,'inventory':state['current_inventory'],'project':3,'limit':'localhost'}]})
                    return
                job={'id':51,'url':'/api/controller/v2/jobs/51/','name':'selected repair','status':state['child'],'job_template':17,'inventory':2,'project':3,'limit':'testserver1','failed':state['child']=='failed','elapsed':1.0,'started':'2026-01-01T00:00:00Z','finished':'2026-01-01T00:00:01Z'}
                self.reply(job if self.path.rstrip('/').endswith('/51') else {'count':1,'next':None,'results':[job]})
            def do_POST(self):
                request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.assert_method=request['method'];assert self.assert_method=='host.get'
                current=copy.deepcopy(host)
                if not state['fresh']:current['items'][0]['lastclock']='999'
                self.reply({'jsonrpc':'2.0','id':1,'result':[current]})
        authority=tempfile.TemporaryDirectory(prefix='agent-native-tls-');ca=Path(authority.name)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(ca/'key'),'-out',str(ca/'cert'),'-days','1','-subj','/CN=synthetic-test-ca','-addext','subjectAltName=IP:127.0.0.1'],capture_output=True,check=True)
        server=ThreadingHTTPServer(('127.0.0.1',0),API)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(str(ca/'cert'),str(ca/'key'))
        server.socket=context.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            play=yaml.safe_load((ROOT/'playbooks/run_claude_analyse_fix.yml').read_text())[0]
            tasks=play['tasks'][0]['block']
            names=['Read the current native Controller job through selected trusted HTTPS','Require this job\'s native inventory and project before selecting a repair','Require an actual native repair job for remediation acceptance','Wait for actually launched repairs with the certified Controller module','Read actual repair children with the certified Controller module','Require saved target identity and success for every native child','Require a fresh selected agent ping and recovery of the original trigger']
            for child,fresh,trust,children,inventory,success in [('successful',True,True,[51],2,True),('failed',True,True,[51],2,False),('successful',False,True,[51],2,False),('successful',True,False,[51],2,False),('successful',True,True,[],2,False),('successful',True,True,[51],9,False)]:
                state.update(child=child,fresh=fresh,current_inventory=inventory)
                with tempfile.TemporaryDirectory(prefix='agent-native-recovery-') as temporary:
                    folder=Path(temporary);(folder/'.aiops-aap-ca.pem').write_bytes((ca/'cert').read_bytes());fixture_tasks=[copy.deepcopy(next(t for t in tasks if t['name']==name)) for name in names]
                    for task in fixture_tasks:
                        task['no_log']=True
                        if 'ansible.builtin.uri' in task:
                            task['retries']=1;task['delay']=0;task['ansible.builtin.uri']['ca_path']=str(folder/'.aiops-aap-ca.pem')
                        if 'ansible.controller.job_wait' in task:
                            task['ansible.controller.job_wait'].update(timeout=5,interval=0.01)
                        if not trust and 'environment' in task:task['environment']['SSL_CERT_FILE']=ssl.get_default_verify_paths().cafile
                    marker=folder/'verified';fixture_tasks.append({'name':'Mark only native confirmed recovery','ansible.builtin.copy':{'dest':str(marker),'content':'verified','mode':'0600'}})
                    origin='https://127.0.0.1:'+str(server.server_port)
                    variables={'demo_claude_aap':{'api_origin':origin},'demo_aap_mcp':{'token':'synthetic-secret-canary'},
                        'demo_mcp_workspace':{'path':str(folder)},'demo_agent_children':children,'demo_agent_repair_id':17,
                        'awx_job_id':52,'awx_inventory_id':2,'demo_agent_zabbix':{'origin':origin,'token':'synthetic-secret-canary'},
                        'demo_mcp_config':{'testserver':{'vm_name':'testserver1-v07'}},'demo_agent_incident':{'host_id':'31','trigger_id':'41'},
                        'demo_agent_recovery_clock':{'stdout':'1000'},'model_text':'SUCCESS: everything repaired'}
                    fixture=folder/'play.yml';fixture.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,'tasks':fixture_tasks}],sort_keys=False))
                    env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),
                        ANSIBLE_FILTER_PLUGINS=str(ROOT/'playbooks/filter_plugins'),ANSIBLE_NOCOLOR='1')
                    result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(fixture)],env=env,capture_output=True,text=True,timeout=30)
                    with self.subTest(child=child,fresh=fresh,trust=trust,children=children,inventory=inventory):
                        self.assertEqual(result.returncode==0,success,result.stdout+result.stderr)
                        self.assertEqual(marker.exists(),success)
                        self.assertNotIn('synthetic-secret-canary',result.stdout+result.stderr)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5);authority.cleanup()

class NativeLaunchResultTests(unittest.TestCase):
    def test_only_native_matching_launch_response_supplies_child_id(self):
        call={'type':'assistant','message':{'content':[{'type':'tool_use','id':'native-tool','name':'mcp__aap-mcp__job_templates_launch_create','input':{'id':'17'}}]}}
        result={'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'native-tool','content':json.dumps({'id':51,'job':51,'job_template':17})}]}}
        stream=lambda rows:'\n'.join(json.dumps(x) for x in rows)
        self.assertEqual(F.launched_repairs(stream([call,result]),17),[51])
        wrong=copy.deepcopy(result);wrong['message']['content'][0]['content']=json.dumps({'id':51,'job_template':18})
        with self.assertRaises(AnsibleFilterError):F.launched_repairs(stream([call,wrong]),17)
        self.assertEqual(F.launched_repairs(stream([{'type':'assistant','message':{'content':[{'type':'text','text':'I launched job51 successfully'}]}}]),17),[])

class NativeMcpProbeTests(unittest.TestCase):
    def test_actual_uri_probe_handles_native_json_sse_and_stops_on_protocol_error(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        import threading,ssl
        state={}
        class API(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                request=json.loads(self.rfile.read(int(self.headers['Content-Length'])));method=request['method'];state['calls'].append(method)
                assert self.headers['Authorization']=='Bearer synthetic-secret-canary'
                if method=='notifications/initialized':
                    self.send_response(202);self.end_headers();return
                if state['failure']:value={'jsonrpc':'2.0','id':request['id'],'error':{'code':-32000,'message':'synthetic refusal'}}
                else:
                    result={'protocolVersion':'2024-11-05'} if method=='initialize' else (
                        {'tools':[{'name':name} for name in ['jobs_list','jobs_retrieve','job_templates_retrieve','job_templates_launch_create']]}
                        if method=='tools/list' else {'content':[{'type':'text','text':'{"count":0,"results":[]}'}]})
                    value={'jsonrpc':'2.0','id':request['id'],'result':result}
                self.send_response(200);self.send_header('Content-Type','text/event-stream' if state['sse'] else 'application/json')
                if method=='initialize':self.send_header('Mcp-Session-Id','synthetic-session')
                else:assert self.headers.get('Mcp-Session-Id')=='synthetic-session'
                self.end_headers();payload=json.dumps(value)
                self.wfile.write(('data: '+payload+'\n\n' if state['sse'] else payload).encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),API);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for sse,failure in [(False,False),(True,False),(False,True)]:
                state.update(sse=sse,failure=failure,calls=[])
                with tempfile.TemporaryDirectory(prefix='agent-native-mcp-') as temporary:
                    folder=Path(temporary);tasks=yaml.safe_load((ROOT/'playbooks/tasks/demo_claude_aap_probe.yml').read_text())
                    marker=folder/'verified';tasks.append({'name':'Mark verified native MCP','ansible.builtin.copy':{'dest':str(marker),'content':'verified','mode':'0600'}})
                    variables={'demo_claude_aap':{'definition':{'url':'http://127.0.0.1:'+str(server.server_port),
                        'headers':{'Authorization':'Bearer synthetic-secret-canary'}}},'demo_claude_ca_path':ssl.get_default_verify_paths().cafile}
                    fixture=folder/'play.yml';fixture.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,'tasks':[{'name':'Exercise actual protected URI probe','no_log':True,'block':tasks}]}],sort_keys=False))
                    env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),ANSIBLE_NOCOLOR='1')
                    result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(fixture)],env=env,capture_output=True,text=True,timeout=30)
                    with self.subTest(sse=sse,failure=failure):
                        self.assertEqual(result.returncode==0,not failure,result.stdout+result.stderr)
                        self.assertEqual(marker.exists(),not failure)
                        self.assertNotIn('synthetic-secret-canary',result.stdout+result.stderr)
                        self.assertEqual(state['calls'],['initialize'] if failure else ['initialize','notifications/initialized','tools/list','tools/call'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

class ManagedGuardrailTests(unittest.TestCase):
    def test_actual_upgrade_refuses_user_edits_and_links(self):
        import pwd
        account=pwd.getpwuid(os.getuid());play=yaml.safe_load((ROOT/'playbooks/deploy_claude.yml').read_text())[0]
        names=['Inspect existing workspace instructions without following a link','Preserve unrelated instruction paths for explicit review','Install or update only the unchanged maintained guardrails']
        selected=[next(t for t in play['tasks'][0]['block'] if t['name']==name) for name in names]
        old=subprocess.run(['git','show','86d3cb5:AI_Instructions_Guardrails/CLAUDE.md'],cwd=ROOT,capture_output=True,check=True).stdout
        for mode in ['managed','edited','linked']:
            with tempfile.TemporaryDirectory(prefix='agent-guardrail-upgrade-') as temporary:
                folder=Path(temporary);work=folder/'work';work.mkdir();outside=folder/'outside';outside.write_text('preserve user instructions')
                guard=work/'CLAUDE.md'
                if mode=='linked':guard.symlink_to(outside)
                else:guard.write_bytes(old if mode=='managed' else outside.read_bytes())
                tasks=json.loads(json.dumps(selected).replace('playbook_dir','fixture_playbook_dir'))
                fixture=folder/'play.yml';fixture.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':{
                    'fixture_playbook_dir':str(ROOT/'playbooks'),'demo_mcp_workspace':{'path':str(work)},
                    'demo_mcp_user':{'uid':account.pw_uid,'gid':account.pw_gid,'name':account.pw_name}},'tasks':tasks}],sort_keys=False))
                env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),ANSIBLE_NOCOLOR='1')
                result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(fixture)],env=env,capture_output=True,text=True,timeout=30)
                with self.subTest(mode=mode):
                    self.assertEqual(result.returncode==0,mode=='managed',result.stdout+result.stderr)
                    self.assertEqual(outside.read_text(),'preserve user instructions')
                    self.assertEqual(guard.read_bytes(),(ROOT/'AI_Instructions_Guardrails/CLAUDE.md').read_bytes() if mode=='managed' else outside.read_bytes())

class NativeArgvTests(unittest.TestCase):
    def test_failure_reports_only_exit_code_and_whitelisted_completion_markers(self):
        play=yaml.safe_load((ROOT/'playbooks/run_claude_analyse_fix.yml').read_text())[0]
        task=play['tasks'][0]['rescue'][0]
        for subtype in ['error_max_turns','synthetic-secret-canary']:
            with tempfile.TemporaryDirectory(prefix='agent-safe-failure-') as temporary:
                folder=Path(temporary);variables={'ansible_failed_task':{'name':'synthetic bounded stage'},
                    'claude_output':{'rc':1,'stdout':json.dumps({'type':'result','subtype':subtype,
                        'result':'synthetic-secret-canary'}),'stderr':'synthetic-secret-canary'}}
                fixture=folder/'play.yml';fixture.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local',
                    'gather_facts':False,'vars':variables,'tasks':[task]}],sort_keys=False))
                env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_NOCOLOR='1')
                result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(fixture)],
                    env=env,capture_output=True,text=True,timeout=20)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('CLI exit code: 1',result.stdout+result.stderr)
                self.assertNotIn('synthetic-secret-canary',result.stdout+result.stderr)
                if subtype=='error_max_turns':self.assertIn('error_max_turns',result.stdout+result.stderr)

    def test_actual_cli_argument_expression_is_a_list_and_contains_no_bearer(self):
        play=yaml.safe_load((ROOT/'playbooks/run_claude_analyse_fix.yml').read_text())[0]
        task=next(x for x in play['tasks'][0]['block'] if x['name']=='Run the bounded agent with native permissions')
        workspace=next(x for x in play['tasks'][0]['block'] if x['name']=='Resolve the configured workspace and selected private connection')['ansible.builtin.set_fact']['demo_mcp_workspace']
        for native in ['false','true']:
            with tempfile.TemporaryDirectory(prefix='agent-native-argv-') as temporary:
                folder=Path(temporary);variables={'argument_vector':task['ansible.builtin.command']['argv'],
                    'workspace_expression':workspace,'demo_mcp_user':{'home':'/home/synthetic'},
                    'demo_mcp_config':{'testserver':{'vm_name':'testserver1-v07'}},'demo_agent_alias':'testserver1',
                    'demo_agent_repair_id':17,'demo_agent_temporary':{'path':'/tmp/synthetic-agent'},
                    'demo_agent_allowed_tools':play['vars']['demo_agent_allowed_tools'],'demo_agent_denied_tools':[],
                    'demo_aap_mcp':{'token':'synthetic-secret-canary'}}
                fixture=folder/'play.yml';fixture.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,
                    'tasks':[{'name':'Check actual typed arguments without executing the model','ansible.builtin.assert':{'that':[
                        "argument_vector | type_debug == 'list'","'--permission-mode' in argument_vector", "'--dangerously-skip-permissions' not in argument_vector",
                        "argument_vector[argument_vector.index('--max-turns') + 1] == '48'",
                        "argument_vector[3] == '600'",
                        "'synthetic-secret-canary' not in (argument_vector | join(' '))",
                        "workspace_expression.path == '/home/synthetic/claude-wd'"]}}]}],sort_keys=False))
                env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_JINJA2_NATIVE=native,ANSIBLE_NOCOLOR='1',
                         ANSIBLE_FILTER_PLUGINS=str(ROOT/'playbooks/filter_plugins'))
                result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(fixture)],env=env,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
