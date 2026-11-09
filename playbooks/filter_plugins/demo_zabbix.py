"""Bind a monitoring clone to the existing AAP allocation and hypervisor."""
import copy
import importlib.util
import ipaddress
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ansible.errors import AnsibleFilterError
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.utils.unsafe_proxy import wrap_var

spec = importlib.util.spec_from_file_location('zabbix_website_configuration', Path(__file__).with_name('demo_website.py'))
website = importlib.util.module_from_spec(spec)
spec.loader.exec_module(website)
guest_spec = importlib.util.spec_from_file_location('zabbix_verified_guests', Path(__file__).with_name('demo_mcp.py'))
guests = importlib.util.module_from_spec(guest_spec)
guest_spec.loader.exec_module(guests)


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def configuration(value):
    result = website.website_configuration(value)
    source = value.get('source_image', {})
    require(source.get('path') == '/opt/vms/zabbix-disk.qcow2'
            and re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', '')),
            'Supply the verified saved monitoring image and its SHA-256.')
    require(re.fullmatch(r'[A-Za-z0-9_-]+', value.get('vm_network', '')),
            'Choose the isolated libvirt network explicitly.')
    user = value.get('guest_user', '')
    require(re.fullmatch(r'[a-z_][a-z0-9_-]*', user) and user != 'root',
            'Supply the cloned guest non-root management account.')
    key = value.get('guest_authorized_public_key', '')
    require(isinstance(key, str) and len(key.split()) == 2,
            'Supply the public counterpart of the attached Machine key.')
    website.website_configuration(dict(value, hypervisor=dict(value['hypervisor'], host_keys=[key])))
    version = f"v{result['instance_number']:02d}"
    result.update(hostname=f"zabbix.{version}.{result['zone']}", record_name=f'zabbix.{version}',
                  website_hostname=f"redhat.{version}.{result['zone']}", version=version,
                  vm_name=f'zabbix-{version}', disk=f'/opt/vms/zabbix-{version}.disk.qcow2',
                  vhost_file=f'/etc/nginx/conf.d/demo-zabbix-{version}.conf',
                  auth_file=f'/etc/nginx/demo-zabbix-{version}.htpasswd', source_image=copy.deepcopy(source),
                  vm_network=value['vm_network'], guest_user=user, guest_authorized_public_key=key,
                  memory_mb=4096, vcpus=2)
    result['testserver'] = guests.guest(result, value.get('testserver'), 'testserver1')
    binding = value.get('cac_import')
    require(isinstance(binding, dict) and set(binding) == {'controller_host', 'inventory_id', 'job_template_id', 'group_id', 'aap_instance_key'}
            and binding['controller_host'] == 'https://' + result['aap_hostname']
            and all(type(binding[key]) is int and binding[key] > 0 for key in ('inventory_id', 'job_template_id', 'group_id'))
            and isinstance(binding['aap_instance_key'], str)
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', binding['aap_instance_key']),
            'Import the selected VM configuration with its existing native AAP importer binding first.')
    result['cac_import'] = copy.deepcopy(binding)
    return result


def metadata(config, host_keys):
    require(isinstance(host_keys, list) and len(host_keys) == 3, 'Retain the newly generated public guest host keys.')
    host_keys = [' '.join(str(key).split()[:2]) for key in host_keys]
    website.website_configuration(dict(config, instance_name=config['instance_name'],
                                      aap_fqdn=config['aap_hostname'],
                                      hypervisor=dict(config['hypervisor'], host_keys=host_keys)))
    return {'schema_version': 1, 'purpose': 'aiops-zabbix', 'instance_name': config['instance_name'],
            'instance_number': config['instance_number'], 'hostname': config['hostname'],
            'hypervisor_machine_id': config['hypervisor']['machine_id'],
            'source_sha256': config['source_image']['sha256'], 'guest_host_keys': host_keys}


def domain_record(xml, config):
    try:
        root = ET.fromstring(xml)
        record = json.loads(root.findtext('description') or '{}')
        expected = metadata(config, record.get('guest_host_keys'))
        require(record == expected, 'The existing domain does not belong to this selected deployment.')
        disks = root.findall("./devices/disk[@device='disk']/source")
        interfaces = root.findall('./devices/interface')
        require(root.findtext('name') == config['vm_name'] and len(disks) == 1
                and disks[0].get('file') == config['disk'] and set(disks[0].attrib) <= {'file', 'index'}
                and ('index' not in disks[0].attrib or re.fullmatch(r'[1-9][0-9]*', disks[0].get('index', ''))),
                'The monitoring domain does not own exactly its expected clone disk.')
        require(len(interfaces) == 1 and interfaces[0].get('type') == 'network'
                and interfaces[0].find('source').get('network') == config['vm_network'],
                'The monitoring domain must use only its declared isolated network.')
        mac = interfaces[0].find('mac').get('address')
        require(re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', mac), 'Require its actual normalized guest MAC.')
        identity = root.findtext('uuid')
        require(re.fullmatch(r'[0-9a-f-]{36}', identity or ''), 'Require the actual domain UUID.')
        return dict(record, uuid=identity, mac=mac, vm_name=config['vm_name'], disk=config['disk'])
    except (ET.ParseError, ValueError, TypeError, AttributeError):
        raise AnsibleFilterError('Invalid or foreign monitoring domain; preserve it for review.') from None


def guest_address(output, mac):
    addresses = re.findall(r'\b' + re.escape(mac) + r'\s+ipv4\s+([0-9.]+)/[0-9]+', output)
    require(len(set(addresses)) == 1, 'Read one DHCP address belonging to this domain MAC.')
    address = ipaddress.IPv4Address(addresses[0])
    require(address.is_private and not address.is_loopback, 'Require the isolated guest private IPv4 address.')
    return str(address)


def network_details(xml, expected):
    try:
        root = ET.fromstring(xml)
        require(root.findtext('name') == expected, 'Inspect exactly the selected guest network.')
        address = ipaddress.IPv4Address(root.find('ip').get('address'))
        bridge = root.find('bridge').get('name')
        require(address.is_private and not address.is_loopback and re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', bridge),
                'Require a local isolated bridge and gateway.')
        return {'gateway': str(address), 'bridge': bridge}
    except (ET.ParseError, ValueError, TypeError, AttributeError):
        raise AnsibleFilterError('Invalid selected guest network.') from None


def quarantine(objects, kind, origin):
    require(isinstance(objects, list), 'Read the cloned monitoring integrations before changing them.')
    key = {'action':'actionid', 'mediatype':'mediatypeid', 'drule':'druleid',
           'host':'hostid', 'httptest':'httptestid', 'script':'scriptid'}[kind]
    updates = []
    for item in objects:
        require(str(item.get(key, '')).isdigit(), 'Require a valid cloned integration identifier.')
        if kind == 'script':
            desired = ({key:item[key], 'url':origin + '/'} if str(item.get('type')) == '6' else
                       {key:item[key], 'type':5, 'scope':1,
                        'command':'throw "Inherited clone integration disabled";', 'timeout':'1s', 'parameters':[]})
        else:
            desired = {key:item[key], 'status':1}
        if any(str(item.get(k)) != str(v) for k,v in desired.items()):
            updates.append(desired)
    return updates


def event_stream(config, value):
    from urllib.parse import urlsplit
    require(isinstance(value, dict), 'Supply the selected AAP event-stream endpoint and Basic authentication.')
    require(set(value) == {'url', 'username', 'password'} and
            all(isinstance(value[k], (str, AnsibleVaultEncryptedUnicode)) for k in value),
            'Supply only the selected event-stream URL and Basic credentials.')
    value = {key: str(item) for key, item in value.items()}
    parsed = urlsplit(value['url'])
    require(parsed.scheme == 'https' and parsed.hostname == config['aap_hostname']
            and parsed.port in (None,443) and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment
            and re.fullmatch(r'/eda-event-streams/api/eda/v1/external_event_stream/[0-9a-f-]{36}/post/', parsed.path),
            'Send monitoring events only to the selected AAP instance event stream.')
    require(all(isinstance(value.get(k),str) and value[k] for k in ('username','password')),
            'Require explicit target event-stream Basic credentials.')
    return copy.deepcopy(value)



def recipient_medias(existing, media_id, endpoint, stale_media_ids=None):
    from urllib.parse import urlsplit
    require(isinstance(existing, list), 'Read the existing cloned notification recipient media.')
    result, selected = [], []
    stale_media_ids = {str(value) for value in (stale_media_ids or [])}
    for entry in existing:
        require(not int(entry.get('provisioned', 0)), 'Review directory-provisioned notification media separately.')
        if str(entry['mediatypeid']) == str(media_id):
            selected.append(entry)
            continue
        destinations = entry['sendto'] if isinstance(entry['sendto'], list) else [entry['sendto']]
        is_eda = str(entry['mediatypeid']) in stale_media_ids or any(re.fullmatch(
            r'/eda-event-streams/api/eda/v1/external_event_stream/[0-9a-f-]{36}/post/',
            urlsplit(str(value)).path) for value in destinations)
        if not is_eda:
            retained = {key: entry[key] for key in ('mediaid', 'mediatypeid', 'sendto', 'active', 'severity', 'period') if key in entry}
            retained['active'] = 1
            result.append(retained)
    require(len(selected) <= 1, 'The selected notification association must be unique.')
    current = {'mediatypeid':str(media_id), 'sendto':endpoint, 'active':0,
               'severity':63, 'period':'1-7,00:00-24:00'}
    if selected and 'mediaid' in selected[0]:
        current['mediaid'] = selected[0]['mediaid']
    result.append(current)
    return result


def reconcile(config, snapshot, monitor_testserver=False):
    """Plan only in-place changes to the known copied monitoring roles."""
    require(isinstance(snapshot, dict) and all(isinstance(snapshot.get(key), list)
            for key in ('hosts', 'items', 'triggers')), 'Read the complete copied monitoring definitions first.')
    require(type(monitor_testserver) is bool, 'Choose selected testserver monitoring explicitly.')
    version = config['version']
    roles = {
        'website': (['demo-website-' + version], 'demo-website-' + version, config['website_hostname']),
        'imported': (['demo-website-redhat', 'demo-website-' + version + '-imported'],
                     'demo-website-' + version + '-imported', 'Imported website ' + version + ' (disabled)'),
        'testserver': (['testserver1', config['testserver']['vm_name']], config['testserver']['vm_name'], config['testserver']['vm_name']),
        'self': (['Zabbix server', config['vm_name']], config['vm_name'], config['hostname']),
        'dashboard': (['demo-aap-dashboard', 'demo-aap-dashboard-' + version],
                      'demo-aap-dashboard-' + version, 'AAP dashboard ' + config['aap_hostname']),
    }
    operations, owned = [], {}
    replacements = {f'redhat.{config["zone"]}':config['website_hostname'],
                    f'aap.{config["zone"]}':config['aap_hostname'], f'zabbix.{config["zone"]}':config['hostname'],
                    f'testserver1.{config["zone"]}':config['testserver']['vm_name'] + '.' + config['zone']}

    def rewrite(value):
        if not isinstance(value, str):
            return value
        for old, new in replacements.items():
            value = re.sub(r'(?<![A-Za-z0-9_.-])' + re.escape(old) + r'(?![A-Za-z0-9_.-])', new, value)
        return re.sub(r'(?<![A-Za-z0-9_.-])testserver1(?![A-Za-z0-9_.-])', config['testserver']['vm_name'], value)

    def update(method, current, identifier, desired):
        changed = {key:value for key,value in desired.items() if str(current.get(key, '')) != str(value)}
        if changed:
            operations.append({'method':method, 'params':dict(changed, **{identifier:current[identifier]})})

    for role, (aliases, name, display) in roles.items():
        matches = [host for host in snapshot['hosts'] if host.get('host') in aliases]
        require(len(matches) <= 1, 'Copied role names collide; preserve both records for review.')
        if not matches:
            require(role not in ('website', 'testserver', 'self'), 'A required copied monitoring role is missing.')
            continue
        host = matches[0]
        require(not any(row.get('host') == name and row.get('hostid') != host['hostid'] for row in snapshot['hosts']),
                'A target monitoring name belongs to another record; do not merge or delete it.')
        owned[str(host['hostid'])] = role
        desired = {'host':name, 'name':display, 'description':rewrite(host.get('description', ''))}
        if role != 'website':
            desired['status'] = 0 if role == 'testserver' and monitor_testserver else 1
        update('host.update', host, 'hostid', desired)
        if role in ('testserver', 'self'):
            address = config['testserver']['address'] if role == 'testserver' else '127.0.0.1'
            for interface in host.get('interfaces', []):
                update('hostinterface.update', interface, 'interfaceid', {'ip':address, 'dns':name, 'useip':1})
        for macro in host.get('macros', []):
            if role == 'dashboard' and macro['macro'] in ('{$BBB.AAP.TOKEN}', '{$BBB.AAP.STREAM_ID}', '{$BBB.AAP.JOB_TEMPLATES}'):
                update('usermacro.update', macro, 'hostmacroid', {'value':'', 'type':0})
            elif role == 'dashboard' and macro['macro'] == '{$BBB.AAP.URL}':
                update('usermacro.update', macro, 'hostmacroid', {'value':'https://' + config['aap_hostname'], 'type':0})
            elif str(macro.get('type', '0')) == '0':
                update('usermacro.update', macro, 'hostmacroid', {'value':rewrite(macro.get('value', ''))})
        if role == 'testserver' and any(item.get('hostid') == host['hostid'] and '{$APACHE.STATUS.HOST}' in item.get('url', '') for item in snapshot['items']):
            macros = [macro for macro in host.get('macros', []) if macro['macro'] == '{$APACHE.STATUS.HOST}']
            require(len(macros) <= 1, 'The target HTTP-check address override must be unique.')
            if macros:
                update('usermacro.update', macros[0], 'hostmacroid', {'value':config['testserver']['address'], 'type':0})
            else:
                operations.append({'method':'usermacro.create', 'params':{'hostid':host['hostid'],
                    'macro':'{$APACHE.STATUS.HOST}', 'value':config['testserver']['address'], 'type':0}})
    for item in snapshot['items']:
        role = owned.get(str(item.get('hostid')))
        if not role or str(item.get('templateid', '0')) != '0':
            continue
        desired = {key:rewrite(item[key]) for key in ('name', 'url', 'description') if key in item}
        if role in ('website', 'imported') and item.get('key_') == 'demo.website.http_status':
            desired.update(url='https://' + config['website_hostname'] + '/content.html',
                name=config['website_hostname'] + ' content HTTP status' + (' (imported, disabled)' if role == 'imported' else ''))
            if role == 'imported':desired['status'] = 1
        if role == 'dashboard' and 'name' in desired and not desired['name'].startswith(config['aap_hostname'] + ': '):
            desired['name'] = config['aap_hostname'] + ': ' + desired['name']
        update('item.update', item, 'itemid', desired)
    for trigger in snapshot['triggers']:
        hosts = trigger.get('hosts', [])
        selected = [owned[str(host['hostid'])] for host in hosts if str(host.get('hostid')) in owned]
        if len(selected) != 1 or str(trigger.get('templateid', '0')) != '0':
            continue
        role = selected[0]
        desired = {key:rewrite(trigger[key]) for key in ('description', 'comments', 'url', 'url_name') if key in trigger}
        if role in ('website', 'imported') and 'Demo website content unavailable' in trigger.get('description', ''):
            desired['description'] = 'Demo website content unavailable: ' + config['website_hostname']
            if role == 'imported':desired.update(description=desired['description'] + ' (imported, disabled)', status=1)
        update('trigger.update', trigger, 'triggerid', desired)
    return operations


def imported_media(objects, selected_id, config, definition):
    name = 'Imported EDA event stream ' + config['version'] + ' (disabled)'
    matches = [row for row in objects if row.get('name') in ('Event-Driven Ansible', name)
               and str(row['mediatypeid']) != str(selected_id)]
    require(len(matches) <= 1 and all(str(row.get('type')) == '4' for row in matches),
            'Review ambiguous imported EDA media before replacing target settings.')
    return [dict(copy.deepcopy(definition), mediatypeid=row['mediatypeid'], name=name, status=1) for row in matches]


def delivery_ready(media, actions, admin, definition, media_id, action_id, trigger_id, endpoint, stale_ids):
    require(isinstance(media, list) and len(media) == 1, 'Read back exactly the selected forwarding media.')
    current = media[0]
    require(str(current['mediatypeid']) == str(media_id) and str(current['status']) == '0'
            and str(current['type']) == '4' and current['script'] == definition['script'],
            'The selected forwarding media does not match its declared script and state.')
    actual = {row['name']:str(row['value']) for row in current.get('parameters', [])}
    expected = {row['name']:str(row['value']) for row in definition['parameters']}
    require(actual == expected and len(current.get('parameters', [])) == len(expected),
            'The selected forwarding endpoint and Basic authentication must match protected settings.')
    selected = [row for row in actions if str(row['actionid']) == str(action_id)]
    require(len(selected) == 1 and all(str(row['status']) == '1' for row in actions),
            'Every action must remain disabled until final deployment validation.')
    conditions = selected[0].get('filter', {}).get('conditions', [])
    require(len(conditions) == 1 and str(conditions[0].get('conditiontype')) == '2'
            and str(conditions[0].get('operator', '0')) == '0' and str(conditions[0].get('value')) == str(trigger_id),
            'The selected forwarding action must refer to this exact monitored trigger.')
    for field in ('operations', 'recovery_operations'):
        operations = selected[0].get(field, [])
        require(len(operations) == 1 and str(operations[0].get('operationtype')) == '0'
                and str(operations[0].get('opmessage', {}).get('mediatypeid')) == str(media_id)
                and [str(row['userid']) for row in operations[0].get('opmessage_usr', [])] == ['1'],
                'Forward only the selected trigger through the selected media and existing recipient.')
    require(len(admin) == 1 and str(admin[0]['userid']) == '1', 'Read the existing notification recipient.')
    associations = admin[0]['medias']
    selected_media = [row for row in associations if str(row['mediatypeid']) == str(media_id)]
    require(len(selected_media) == 1 and str(selected_media[0]['active']) == '0', 'Keep one active selected notification association.')
    destinations = selected_media[0]['sendto']
    require((destinations if isinstance(destinations, list) else [destinations]) == [endpoint],
            'The selected recipient must use the current target event stream.')
    cleaned = recipient_medias(associations, media_id, endpoint, stale_ids)
    require(len(cleaned) == len(associations)
            and all(str(row.get('active')) == '1' for row in associations if str(row['mediatypeid']) != str(media_id)),
            'Stale EDA destinations must be removed and unrelated recipient media remain disabled.')
    return True



def provenance(config, record, address=None, network=None, machine_id=None):
    result = {'schema_version':1, 'instance_name':config['instance_name'],
              'instance_number':config['instance_number'], 'vm_name':config['vm_name'],
              'uuid':record['uuid'], 'disk':config['disk'], 'mac':record['mac'],
              'guest_host_keys':record['guest_host_keys'], 'host_keys':record['guest_host_keys'],
              'network':config['vm_network'], 'user':config['guest_user'], 'port':22, 'verified':False,
              'source_sha256':config['source_image']['sha256'],
              'hypervisor_machine_id':config['hypervisor']['machine_id'], 'public_hostname':config['hostname'],
              'nginx_file':config['vhost_file'], 'auth_file':config['auth_file'], 'certificate':config['hostname']}
    if address:
        require(guest_address(record['mac'] + ' ipv4 ' + address + '/32', record['mac']) == address,
                'Retain only the verified private guest address.')
        result.update(ip=address, address=address, api_url='http://' + address + '/api_jsonrpc.php')
    if network is not None:
        require(isinstance(network, dict) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', network.get('bridge', '')),
                'Retain the actual verified libvirt bridge.')
        result['bridge'] = network['bridge']
        if 'gateway' in network:
            gateway = ipaddress.IPv4Address(network['gateway'])
            require(str(gateway) == network['gateway'] and gateway.is_private,
                    'Retain only the observed private bridge gateway.')
            result['gateway'] = str(gateway)
    if machine_id is not None:
        require(address is not None and network is not None and isinstance(machine_id, str)
                and re.fullmatch(r'[0-9a-f]{32}', machine_id) and machine_id != config['hypervisor']['machine_id'],
                'Require the pinned SSH guest machine identity before marking ownership verified.')
        result.update(machine_id=machine_id, verified=True)
    return result


def source_inventory_variables(config, resource, rows):
    """Validate the native inventory update; retain unrelated existing variables."""
    require(isinstance(rows, list) and len(rows) <= 256 and resource.get('verified') is True
            and resource.get('instance_name') == config['instance_name']
            and resource.get('vm_name') == config['vm_name']
            and resource.get('hypervisor_machine_id') == config['hypervisor']['machine_id']
            and isinstance(resource.get('gateway'), str),
            'Publish only the authenticated selected guest and its observed gateway.')
    selected = []
    immutable = ('uuid', 'disk', 'network', 'bridge', 'mac', 'address', 'machine_id',
                 'hypervisor_machine_id', 'host_keys', 'user', 'port', 'source_sha256', 'gateway')
    for row in rows:
        require(isinstance(row, dict) and row.get('inventory') == config['cac_import']['inventory_id'],
                'Use only the existing importer inventory.')
        value = row.get('variables') or {}
        value = AnsibleLoader(value).get_single_data() if isinstance(value, str) else copy.deepcopy(value)
        require(isinstance(value, dict) and isinstance(value.get('vm_resource', {}), dict),
                'Preserve invalid existing source inventory variables for review.')
        saved = value.get('vm_resource', {})
        if row.get('name') == config['vm_name']:
            require(all(field not in saved or saved[field] == resource[field] for field in immutable),
                    'Existing source inventory ownership conflicts with this verified guest.')
            selected.append(value)
        else:
            require(not any(saved.get(field) == resource[field] for field in ('uuid', 'mac', 'machine_id'))
                    and value.get('vm_uuid') != resource['uuid'] and value.get('machine_id') != resource['machine_id']
                    and not (value.get('ansible_host') == resource['address']
                             and value.get('hypervisor_host') in (None, config['hypervisor']['name']))
                    and not (saved.get('address') == resource['address']
                             and saved.get('hypervisor_machine_id') == resource['hypervisor_machine_id']),
                    'Another source inventory host owns this guest identity.')
    require(len(selected) <= 1, 'The selected VM has duplicate source inventory rows.')
    result = selected[0] if selected else {}
    desired = {'aap_instance_number': config['instance_number'], 'hypervisor_host': config['hypervisor']['name'],
               'ansible_host': resource['address'], 'ansible_user': resource['user'], 'ansible_port': resource['port'],
               'vm_uuid': resource['uuid'], 'machine_id': resource['machine_id'], 'host_keys': resource['host_keys']}
    require(all(key not in result or result[key] == value for key, value in desired.items()),
            'Existing source connection fields conflict with this guest.')
    result.update(desired)
    result['vm_resource'] = dict(result.get('vm_resource', {}), **copy.deepcopy(resource))
    return wrap_var(result)


class FilterModule:
    def filters(self):
        return {'demo_zabbix_configuration':configuration, 'demo_zabbix_metadata':metadata,
                'demo_zabbix_domain_record':domain_record, 'demo_zabbix_guest_address':guest_address,
                'demo_zabbix_network_details':network_details, 'demo_zabbix_quarantine':quarantine,
                'demo_zabbix_event_stream':event_stream, 'demo_zabbix_recipient_medias':recipient_medias,
                'demo_zabbix_provenance':provenance, 'demo_zabbix_reconciliation':reconcile,
                'demo_zabbix_source_inventory_variables':source_inventory_variables,
                'demo_zabbix_imported_media':imported_media, 'demo_zabbix_delivery_ready':delivery_ready}
