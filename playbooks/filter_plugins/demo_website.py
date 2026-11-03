"""Validate a selected AAP allocation and derive its website configuration."""

import base64
import ipaddress
import re

from ansible.errors import AnsibleFilterError


def website_configuration(deployment):
    """Use the existing allocation number; never allocate or infer a target."""
    try:
        if not isinstance(deployment, dict):
            raise ValueError("The selected website deployment must be a mapping.")
        number = deployment["instance_number"]
        if isinstance(number, bool) or not re.fullmatch(r"[1-9][0-9]*", str(number)):
            raise ValueError("A positive existing AAP allocation number is required.")
        number = int(number)
        if deployment["instance_name"] != f"aap27-test-{number}":
            raise ValueError("The instance name and its allocation number differ.")
        zone = deployment["zone"]
        if not isinstance(zone, str) or len(zone) > 190 or not re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
            r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", zone
        ):
            raise ValueError("An explicit DNS zone is required.")
        version = f"v{number:02d}"
        aap_hostname = f"aap27.{version}.{zone}"
        if deployment["aap_fqdn"] != aap_hostname:
            raise ValueError("The selected AAP FQDN does not match its allocation.")
        hypervisor = deployment["hypervisor"]
        if not isinstance(hypervisor, dict) or not hypervisor.get("name"):
            raise ValueError("The selected instance must identify its hypervisor.")
        address = str(ipaddress.IPv4Address(hypervisor["address"]))
        public_ip = ipaddress.IPv4Address(hypervisor["public_ipv4"])
        if not public_ip.is_global:
            raise ValueError("The website requires the selected hypervisor's public IPv4 address.")
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", hypervisor["user"]):
            raise ValueError("The selected hypervisor requires an explicit SSH user.")
        port = int(hypervisor["port"])
        if isinstance(hypervisor["port"], bool) or not 1 <= port <= 65535:
            raise ValueError("The selected hypervisor SSH port is invalid.")
        if not re.fullmatch(r"[0-9a-f]{32}", hypervisor["machine_id"]):
            raise ValueError("The selected hypervisor machine identity is required.")
        keys = hypervisor["host_keys"]
        if not isinstance(keys, list) or not keys:
            raise ValueError("Pinned hypervisor SSH public keys are required.")
        for key in keys:
            parts = key.split()
            if len(parts) != 2 or parts[0] not in {
                "ssh-ed25519", "ssh-rsa", "ecdsa-sha2-nistp256",
                "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521",
            }:
                raise ValueError("A pinned SSH public key is malformed.")
            base64.b64decode(parts[1], validate=True)
        prefix = f"demo-website-{version}"
        return {
            "instance_name": deployment["instance_name"], "instance_number": number,
            "zone": zone, "record_name": f"redhat.{version}",
            "hostname": f"redhat.{version}.{zone}", "aap_hostname": aap_hostname,
            "hypervisor": dict(hypervisor, address=address, public_ipv4=str(public_ip), port=port),
            "root": f"/var/www/redhat-{version}",
            "checkout": f"/opt/demo-web-src-{version}",
            "rate_limit_file": f"/etc/nginx/{prefix}-rate-limit.conf",
            "rate_limit_zone": f"redhat_{version}_panic",
            "cache_zone": f"redhat_{version}_deliveries",
            "cache_path": f"/var/cache/nginx/{prefix}",
            "vhost_file": f"/etc/nginx/conf.d/{prefix}.conf",
        }
    except (KeyError, TypeError, ValueError) as error:
        raise AnsibleFilterError(str(error)) from error


def safe_dns_records(records, expected_address):
    """Permit creation or an identical record, never replacement of another site."""
    return isinstance(records, list) and all(
        isinstance(record, dict) and record.get("type") == "A"
        and record.get("data") == expected_address for record in records
    )


class FilterModule:
    def filters(self):
        return {
            "demo_website_configuration": website_configuration,
            "demo_website_safe_dns_records": safe_dns_records,
        }
