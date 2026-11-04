"""Enable only verified Linux/ICMP checks while retaining copied Apache history."""

from ansible.errors import AnsibleFilterError
import xml.etree.ElementTree as ET


def require(value, message):
    if not value:
        raise AnsibleFilterError(message)


def domain_matches(config, xml):
    try:
        guest = config['testserver']
        root = ET.fromstring(xml)
        disks = root.findall('./devices/disk[@device="disk"]/source')
        interfaces = root.findall('./devices/interface')
        require(root.findtext('name') == guest['vm_name'] and root.findtext('uuid') == guest['uuid']
            and len(disks) == 1 and disks[0].get('file') == guest['disk']
            and len(interfaces) == 1 and interfaces[0].get('type') == 'network'
            and interfaces[0].find('mac').get('address') == guest['mac']
            and interfaces[0].find('source').get('network') == guest['network'],
            'The selected testserver does not match its verified domain identity.')
        return True
    except (ET.ParseError, KeyError, TypeError, AttributeError):
        raise AnsibleFilterError('Read the exact selected testserver domain before enabling its monitoring.') from None


def monitoring_plan(config, snapshot):
    require(isinstance(snapshot, dict) and isinstance(snapshot.get('host'), dict)
        and all(isinstance(snapshot.get(field), list) for field in ('items', 'triggers', 'discovery_rules',
            'template_items', 'template_triggers', 'template_discovery_rules')),
        'Read complete selected-host and template definitions before enabling monitoring.')
    host, guest = snapshot['host'], config['testserver']
    require(host.get('host') == guest['vm_name'] and str(host.get('hostid', '')).isdigit(),
        'Enable only the selected versioned testserver monitoring host.')
    interfaces = host.get('interfaces', [])
    require(len(interfaces) == 1 and str(interfaces[0].get('type')) == '1'
        and interfaces[0].get('ip') == guest['address'] and str(interfaces[0].get('useip')) == '1',
        'The monitoring interface must use only the verified selected private guest address.')
    known = {'Linux by Zabbix agent': 'linux', 'ICMP Ping': 'icmp', 'Apache by HTTP': 'apache'}
    templates = host.get('parentTemplates', [])
    require(isinstance(templates, list) and templates
        and all(row.get('name') in known and str(row.get('templateid', '')).isdigit() for row in templates)
        and len({row['name'] for row in templates}) == len(templates)
        and len({str(row['templateid']) for row in templates}) == len(templates),
        'Review unknown or ambiguous copied templates before enabling the testserver.')
    roles = {str(row['templateid']): known[row['name']] for row in templates}
    require({'linux', 'icmp'} <= set(roles.values()), 'The selected guest needs the reviewed Linux and ICMP templates.')

    def parent_roles(rows, identifier, is_trigger=False):
        result = {}
        for row in rows:
            owners = row.get('hosts', []) if is_trigger else [{'hostid': row.get('hostid')}]
            require(len(owners) == 1 and str(owners[0].get('hostid')) in roles
                and str(row.get(identifier, '')).isdigit() and str(row[identifier]) not in result,
                'Template definitions must belong only to the selected reviewed templates.')
            result[str(row[identifier])] = roles[str(owners[0]['hostid'])]
        return result

    item_roles = parent_roles(snapshot['template_items'], 'itemid')
    trigger_roles = parent_roles(snapshot['template_triggers'], 'triggerid', True)
    discovery_roles = parent_roles(snapshot['template_discovery_rules'], 'itemid')
    host_rules = {}
    operations, affected = [], {'linux': 0, 'icmp': 0, 'apache': 0}

    def update(method, row, identifier, role):
        require(str(row.get(identifier, '')).isdigit(), 'Require the existing check identifier before status changes.')
        status = 1 if role == 'apache' else 0
        if str(row.get('status')) != str(status):
            operations.append({'method': method, 'params': {identifier: row[identifier], 'status': status}})

    for rule in snapshot['discovery_rules']:
        role = discovery_roles.get(str(rule.get('templateid')))
        require(role is not None and str(rule.get('hostid')) == str(host['hostid']),
            'Every selected discovery rule must retain reviewed template ownership.')
        host_rules[str(rule['itemid'])] = role
        update('discoveryrule.update', rule, 'itemid', role)

    def classify(row, parents):
        role = parents.get(str(row.get('templateid')))
        if role is None:
            discovery = row.get('discoveryRule')
            if isinstance(discovery, dict):
                role = host_rules.get(str(discovery.get('itemid')))
        require(role is not None, 'An unclassified copied check remains; review it before enabling this host.')
        return role

    health = {}
    for item in snapshot['items']:
        require(str(item.get('hostid')) == str(host['hostid']), 'Do not change another monitoring host item.')
        role = classify(item, item_roles)
        affected[role] += 1
        update('item.update', item, 'itemid', role)
        if item.get('key_') in ('agent.ping', 'system.uptime', 'icmpping'):
            require(item['key_'] not in health and role in ('linux', 'icmp') and str(item.get('value_type')) == '3',
                'Read one unsigned numeric item for each selected health check.')
            health[item['key_']] = str(item['itemid'])
    for trigger in snapshot['triggers']:
        require(trigger.get('hosts') and all(str(row.get('hostid')) == str(host['hostid']) for row in trigger['hosts']),
            'Do not enable a cross-host copied trigger.')
        update('trigger.update', trigger, 'triggerid', classify(trigger, trigger_roles))
    require(set(health) == {'agent.ping', 'system.uptime', 'icmpping'}, 'The selected agent/uptime/ICMP health items are incomplete.')
    if str(host.get('status')) != '0':
        operations.append({'method': 'host.update', 'params': {'hostid': host['hostid'], 'status': 0}})
    return {'operations': operations, 'health_items': health, 'item_counts': affected, 'hostid': str(host['hostid'])}


def samples_ready(rows, items, since):
    if not isinstance(rows, list) or not isinstance(items, dict) or set(items) != {'agent.ping', 'system.uptime', 'icmpping'}:
        return False
    try:
        for name, identifier in items.items():
            samples = [row for row in rows if str(row.get('itemid')) == str(identifier) and int(row['clock']) >= int(since)]
            if not samples or not any(float(row['value']) > 0 and (name == 'system.uptime' or float(row['value']) == 1) for row in samples):
                return False
        return True
    except (ValueError, TypeError, KeyError):
        return False


class FilterModule:
    def filters(self):
        return {'demo_zabbix_testserver_domain': domain_matches,
                'demo_zabbix_testserver_plan': monitoring_plan,
                'demo_zabbix_testserver_samples_ready': samples_ready}
