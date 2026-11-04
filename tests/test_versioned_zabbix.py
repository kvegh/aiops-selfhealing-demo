"""Exercise clone ownership, safe startup and secret-free native webhook delivery."""
import copy, importlib.util, json, os, shutil, subprocess, sys, tempfile, threading, unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import yaml
from ansible.errors import AnsibleFilterError
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('versioned_zabbix',ROOT/'playbooks/filter_plugins/demo_zabbix.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)

def deployment():
    return {'instance_name':'aap27-test-7','instance_number':7,'aap_fqdn':'aap27.v07.example.invalid','zone':'example.invalid',
        'hypervisor':{'name':'recovery','address':'192.0.2.50','public_ipv4':'8.8.8.8','user':'automation','port':22,'machine_id':'1'*32,'host_keys':['ssh-ed25519 AAAA']},
        'source_image':{'path':'/opt/vms/zabbix-disk.qcow2','sha256':'a'*64},'vm_network':'isolated','guest_user':'automation','guest_authorized_public_key':'ssh-ed25519 AAAA'}

class VersionedZabbixTests(unittest.TestCase):
    def test_allocation_controls_every_guest_and_public_resource(self):
        result=policy.configuration(deployment())
        self.assertEqual(result['vm_name'],'zabbix-v07');self.assertEqual(result['hostname'],'zabbix.v07.example.invalid')
        self.assertEqual(result['website_hostname'],'redhat.v07.example.invalid')
        self.assertEqual(result['disk'],'/opt/vms/zabbix-v07.disk.qcow2')
        self.assertEqual(result['vhost_file'],'/etc/nginx/conf.d/demo-zabbix-v07.conf')
        self.assertEqual(result['auth_file'],'/etc/nginx/demo-zabbix-v07.htpasswd')
        for key,value in [('instance_number',8),('guest_user','root'),('guest_authorized_public_key',''),('source_image',{'path':'/foreign','sha256':'a'*64})]:
            invalid=deployment();invalid[key]=value
            with self.assertRaises(AnsibleFilterError):policy.configuration(invalid)

    def test_native_metadata_disk_network_and_public_keys_must_all_belong_to_the_allocation(self):
        import xml.etree.ElementTree as E
        config=policy.configuration(deployment());record=policy.metadata(config,['ssh-ed25519 AAAA']*3)
        root=E.Element('domain');E.SubElement(root,'name').text=config['vm_name'];E.SubElement(root,'uuid').text='11111111-1111-1111-1111-111111111111'
        E.SubElement(root,'description').text=json.dumps(record);devices=E.SubElement(root,'devices')
        disk=E.SubElement(devices,'disk',device='disk');E.SubElement(disk,'source',file=config['disk'])
        interface=E.SubElement(devices,'interface',type='network');E.SubElement(interface,'source',network='isolated');E.SubElement(interface,'mac',address='52:54:00:12:34:56')
        xml=E.tostring(root).decode();result=policy.domain_record(xml,config);self.assertEqual(result['guest_host_keys'],record['guest_host_keys'])
        early=policy.provenance(config,result);self.assertNotIn('ip',early)
        self.assertFalse(early['verified'])
        routed=policy.provenance(config,result,'192.0.2.123');self.assertEqual(routed['api_url'],'http://192.0.2.123/api_jsonrpc.php')
        self.assertNotIn('token',routed);self.assertNotIn('password',routed)
        verified=policy.provenance(config,result,'192.0.2.123',{'bridge':'vmbr0','gateway':'192.0.2.1'},'2'*32)
        self.assertTrue(verified['verified']);self.assertEqual(verified['machine_id'],'2'*32)
        self.assertEqual(verified['address'],'192.0.2.123');self.assertEqual(verified['bridge'],'vmbr0')
        self.assertEqual(verified['network'],'isolated');self.assertEqual(verified['host_keys'],record['guest_host_keys'])
        for identity in ('', '1'*32, 'not-a-machine-id'):
            with self.assertRaises(AnsibleFilterError):policy.provenance(config,result,'192.0.2.123',{'bridge':'vmbr0'},identity)
        indexed=xml.replace('file="'+config['disk']+'"','file="'+config['disk']+'" index="1"')
        self.assertEqual(policy.domain_record(indexed,config),result)
        for source_extra in (' index="0"',' protocol="https"',' index="x"'):
            invalid=xml.replace('file="'+config['disk']+'"','file="'+config['disk']+'"'+source_extra)
            with self.assertRaises(AnsibleFilterError):policy.domain_record(invalid,config)
        for invalid in (xml.replace('zabbix-v07.disk','production.disk'),xml.replace('network="isolated"','network="foreign"'),xml.replace('aap27-test-7','aap27-test-8')):
            with self.assertRaises(AnsibleFilterError):policy.domain_record(invalid,config)
        self.assertEqual(policy.guest_address('vnet0 52:54:00:12:34:56 ipv4 192.0.2.123/24',result['mac']),'192.0.2.123')
        with self.assertRaises(AnsibleFilterError):policy.guest_address('vnet0 52:54:00:12:34:57 ipv4 192.0.2.123/24',result['mac'])

    def test_delivery_cannot_target_production_or_another_version(self):
        config=policy.configuration(deployment());path='/eda-event-streams/api/eda/v1/external_event_stream/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/post/'
        value={'url':'https://aap27.v07.example.invalid'+path,'username':'synthetic-user','password':'synthetic-password'}
        self.assertEqual(policy.event_stream(config,value),value)
        for origin in ('https://aap27.v08.example.invalid','http://aap27.v07.example.invalid','https://production.example.invalid'):
            with self.assertRaises(AnsibleFilterError):policy.event_stream(config,dict(value,url=origin+path))

    @unittest.skipUnless(shutil.which('node'),'requires existing Node.js')
    def test_webhook_omits_credentials_from_payload_and_output(self):
        source=(ROOT/'playbooks/files/demo-zabbix-event-stream.js').read_text()
        fixture={'endpoint':'https://target.example.invalid/events','username':'synthetic-canary-user','password':'synthetic-canary-password','event_id':'7','event_name':'Demo website content unavailable','event_value':'1','trigger_id':'8','host_host':'demo-website-v07'}
        code="""const fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));let captured;
global.btoa=x=>Buffer.from(x).toString('base64');global.HttpRequest=class {addHeader(x){} post(u,d){captured=JSON.parse(d)} getStatus(){return 200}};
const output=new Function('value',input.source)(JSON.stringify(input.fixture));process.stdout.write(JSON.stringify({captured,output}));"""
        result=subprocess.run(['node','-e',code],input=json.dumps({'source':source,'fixture':fixture}),text=True,capture_output=True,check=True)
        self.assertNotIn(fixture['password'],result.stdout+result.stderr);self.assertNotIn(fixture['username'],result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['captured']['event_value'],1)

class Api:
    def __init__(self,reject):
        self.reject=reject;self.calls=[];self.tables={
            'action':[{'actionid':'7','name':'inherited action','status':'0'}],
            'mediatype':[{'mediatypeid':'72','name':'inherited media','status':'0'}],
            'drule':[{'druleid':'1','status':'0'}],'httptest':[{'httptestid':'1','status':'0'}],
            'host':[{'hostid':'1','host':'inherited-host','status':'0'}],
            'script':[{'scriptid':'1','type':'0','scope':'1','command':'inherited command','url':''}],
            'hostgroup':[],'item':[],'trigger':[],
            'user':[{'userid':'1','medias':[{'mediatypeid':'72','sendto':'https://source.example.invalid','active':'0','severity':'63','period':'1-7,00:00-24:00'}]}]}
        self.ids={'hostgroup':'groupid',**{x:x+'id' for x in ('host','item','trigger','action','mediatype','drule','httptest','script','user')}}
    def operation(self,body):
        method=body['method'];params=body['params'];self.calls.append((method,copy.deepcopy(params)))
        if method=='apiinfo.version':return {'result':'7.4.12'}
        if self.reject and method=='action.update':return {'error':{'code':-1,'message':'Synthetic rejected quarantine'}}
        kind,operation=method.split('.');key=self.ids[kind];rows=self.tables[kind]
        if operation=='get':
            chosen=rows
            for field,values in params.get('filter',{}).items():
                if not isinstance(values,list):values=[values]
                chosen=[r for r in chosen if str(r.get(field)) in [str(v) for v in values]]
            if params.get('hostids'):chosen=[r for r in chosen if str(r.get('hostid')) in params['hostids']]
            return {'result':str(len(chosen)) if params.get('countOutput') else copy.deepcopy(chosen)}
        if operation=='create':
            identity=str(1000+len(rows));row=dict(copy.deepcopy(params),**{key:identity})
            if kind=='trigger':row['hostid']=next(x['hostid'] for x in self.tables['host'] if x.get('host')=='demo-website-v07')
            rows.append(row)
        else:identity=str(params[key]);next(r for r in rows if str(r[key])==identity).update(copy.deepcopy(params))
        return {'result':{key+'s':[identity]}}

class QuarantineExecutionTests(unittest.TestCase):
    def run_tasks(self,reject=False,api=None,unsafe=False,vaulted=False):
        api=api or Api(reject)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if body['method']!='apiinfo.version' and self.headers.get('Authorization')!='Bearer synthetic-clone-bearer':self.send_response(401);self.end_headers();return
                result=dict(api.operation(body),jsonrpc='2.0',id=body['id']);self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(result).encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix='zabbix-api-fixture-') as directory:
                folder=Path(directory);marker=folder/'server-started'
                for original in (ROOT/'playbooks/tasks').glob('demo_zabbix_*.yml'):
                    (folder/original.name).write_text(original.read_text().replace('http://127.0.0.1/api_jsonrpc.php',f'http://127.0.0.1:{server.server_address[1]}/api_jsonrpc.php'))
                tasks=yaml.safe_load((folder/'demo_zabbix_monitoring.yml').read_text())
                next(row for row in tasks if row['name']=='Stop and mask the monitoring server before inspecting inherited integrations')['ansible.builtin.command']['argv']=[sys.executable,'-c','print("masked")']
                next(row for row in tasks if row['name']=='Require the selected versioned guest hostname')['ansible.builtin.command']['argv']=[sys.executable,'-c','print("zabbix.v07.example.invalid")']
                hosts=folder/'hosts';hosts.write_text('127.0.0.1 localhost\n192.0.2.1 redhat.v07.example.invalid aap27.v07.example.invalid zabbix.v07.example.invalid\n')
                next(row for row in tasks if row['name']=='Keep the selected guest first in its owned frontend proxy aliases')['ansible.builtin.lineinfile']['path']=str(hosts)
                tasks[-1].pop('ansible.builtin.systemd_service');tasks[-1]['ansible.builtin.command']={'argv':[sys.executable,'-c','from pathlib import Path;import sys;Path(sys.argv[1]).touch()',str(marker)]};tasks[-1]['changed_when']=True
                (folder/'files').mkdir();shutil.copy(ROOT/'playbooks/files/demo-zabbix-event-stream.js',folder/'files')
                variables={'demo_zabbix_config':policy.configuration(deployment()),'demo_zabbix_network':{'gateway':'192.0.2.1','bridge':'vmbr0'},'demo_zabbix_clone_api_token':'synthetic-clone-bearer','demo_zabbix_delivery':{'url':'https://aap27.v07.example.invalid/events','username':'synthetic-user','password':'synthetic-password'},'demo_zabbix_enable_delivery':False}
                if unsafe:
                    from ansible.utils.unsafe_proxy import wrap_var
                    variables['demo_zabbix_clone_api_token']=wrap_var(variables['demo_zabbix_clone_api_token'])
                    variables['demo_zabbix_delivery']=wrap_var(variables['demo_zabbix_delivery'])
                vault_arguments=[]
                if vaulted:
                    from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode
                    from ansible.parsing.vault import VaultLib,VaultSecret
                    secret=VaultSecret(b'synthetic-vault-password');vault=VaultLib([('default',secret)])
                    variables['demo_zabbix_clone_api_token']=AnsibleVaultEncryptedUnicode.from_plaintext(variables['demo_zabbix_clone_api_token'],vault,secret)
                    variables['demo_zabbix_delivery']={key:AnsibleVaultEncryptedUnicode.from_plaintext(value,vault,secret) for key,value in variables['demo_zabbix_delivery'].items()}
                    password_file=folder/'vault-password';password_file.write_text('synthetic-vault-password');password_file.chmod(0o600)
                    vault_arguments=['--vault-password-file',str(password_file)]
                    policy.event_stream(variables['demo_zabbix_config'],dict(variables['demo_zabbix_delivery'],url=AnsibleVaultEncryptedUnicode.from_plaintext('https://aap27.v07.example.invalid/eda-event-streams/api/eda/v1/external_event_stream/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/post/',vault,secret)))
                from ansible.parsing.yaml.dumper import AnsibleDumper
                path=folder/'play.yml';path.write_text(yaml.dump([{'hosts':'localhost','connection':'local','gather_facts':False,'vars':variables,'tasks':tasks}],Dumper=AnsibleDumper,sort_keys=False))
                environment=dict(os.environ,ANSIBLE_FILTER_PLUGINS=str(ROOT/'playbooks/filter_plugins'),ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),ANSIBLE_NOCOLOR='1')
                response=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',*vault_arguments,str(path)],cwd=folder,env=environment,text=True,capture_output=True,timeout=150)
                self.assertEqual(hosts.read_text(),'127.0.0.1 localhost\n192.0.2.1 zabbix.v07.example.invalid redhat.v07.example.invalid aap27.v07.example.invalid\n')
                return response,marker.exists(),api
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
    def test_rejected_quarantine_never_starts_the_server(self):
        result,started,api=self.run_tasks(True);self.assertNotEqual(result.returncode,0,result.stdout+result.stderr);self.assertFalse(started);self.assertIn('action.update',[x[0] for x in api.calls])
    def test_only_target_monitoring_starts_after_inherited_integrations_are_disabled(self):
        result,started,api=self.run_tasks();self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertTrue(started)
        for kind in ('action','mediatype','drule','host','httptest'):self.assertEqual(int(api.tables[kind][0]['status']),1)
        self.assertIn('Inherited clone integration disabled',api.tables['script'][0]['command'])
        target=next(x for x in api.tables['host'] if x.get('host')=='demo-website-v07');self.assertEqual(int(target['status']),0)
        item=api.tables['item'][0];self.assertEqual(item['url'],'https://redhat.v07.example.invalid/content.html');self.assertEqual(item['verify_peer'],1)
        self.assertEqual(int(next(x for x in api.tables['action'] if x.get('name')=='AIOps v07 website events')['status']),1)

    def test_rerun_reuses_monitoring_and_delivery_objects(self):
        first,started,api=self.run_tasks();self.assertEqual(first.returncode,0,first.stdout+first.stderr)
        identities={key:[row[api.ids[key]] for row in rows] for key,rows in api.tables.items()}
        second,started,api=self.run_tasks(api=api);self.assertEqual(second.returncode,0,second.stdout+second.stderr)
        self.assertTrue(started)
        self.assertEqual({key:[row[api.ids[key]] for row in rows] for key,rows in api.tables.items()},identities)

    def test_protected_injected_values_do_not_leave_api_configuration_unrendered(self):
        result,started,api=self.run_tasks(unsafe=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(started)
        media=next(x for x in api.tables['mediatype'] if x.get('name')=='AIOps v07 event stream')
        self.assertIn('new HttpRequest()',media['script'])
        parameters={x['name']:x['value'] for x in media['parameters']}
        self.assertEqual(parameters['password'],'synthetic-password')
        self.assertEqual(parameters['event_name'],'{EVENT.NAME}')

    def test_native_cli_vault_variables_reach_only_the_selected_guest_api(self):
        # Component coverage for native Ansible Vault values in a vars file;
        # Controller launch extra_vars do not support inline Vault transport.
        result,started,api=self.run_tasks(vaulted=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(started)
        media=next(x for x in api.tables['mediatype'] if x.get('name')=='AIOps v07 event stream')
        parameters={x['name']:x['value'] for x in media['parameters']}
        self.assertEqual(parameters['password'],'synthetic-password')

if __name__=='__main__':unittest.main()
