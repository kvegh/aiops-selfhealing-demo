"""Configure native Zabbix AAP metrics from the project's encrypted myvars."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def load_settings(vault_file, password_file):
    with tempfile.TemporaryDirectory(prefix="bbb-vars-") as task_temp:
        environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=task_temp)
        result = subprocess.run(
            ["ansible-inventory", "-i", "localhost,", "--list", "--extra-vars",
             "@" + str(vault_file), "--vault-password-file", str(password_file)],
            capture_output=True, text=True, env=environment, check=True,
        )
    return json.loads(result.stdout)["_meta"]["hostvars"]["localhost"]


class Zabbix:
    def __init__(self, settings):
        self.url = settings["demo_zabbix_api_url"]
        self.token = settings["demo_zabbix_api_token"]

    def api(self, method, params):
        request = urllib.request.Request(
            self.url,
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                             "params": params}).encode(),
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json-rpc"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
        if "error" in data:
            raise RuntimeError(method + ": " + data["error"]["message"])
        return data["result"]


def javascript(filename):
    return [{"type": 21, "params": (ROOT / "src" / "aap_dashboard" / filename).read_text(),
             "error_handler": 0}]


def jsonpath(expression):
    return [{"type": 12, "params": expression, "error_handler": 0}]


def configure(settings):
    zabbix = Zabbix(settings)
    hosts = zabbix.api("host.get", {
        "filter": {"host": "demo-aap-dashboard"}, "output": ["hostid"],
    })
    if hosts:
        if len(hosts) != 1:
            raise RuntimeError("Expected one AAP dashboard host")
        host_id = hosts[0]["hostid"]
    else:
        host_id = zabbix.api("host.create", {
            "host": "demo-aap-dashboard", "name": "AAP demo monitoring", "status": 0,
            "groups": [{"groupid": settings["demo_zabbix_demo_host_group_id"]}],
            "interfaces": [],
        })["hostids"][0]

    macros = {
        "{$BBB.AAP.URL}": (settings["demo_aap_api_url"].rstrip("/"), 0),
        "{$BBB.AAP.TOKEN}": (settings["demo_aap_dashboard_api_token"], 1),
        "{$BBB.AAP.STREAM_ID}": (str(settings["demo_aap_event_stream_id"]), 0),
        "{$BBB.AAP.JOB_TEMPLATES}": (",".join(map(str, settings["demo_aap_job_template_ids"])), 0),
    }
    existing = {macro["macro"]: macro["hostmacroid"] for macro in zabbix.api("usermacro.get", {
        "hostids": [host_id], "output": ["hostmacroid", "macro"],
    })}
    for name, (value, kind) in macros.items():
        params = {"macro": name, "value": value, "type": kind}
        if name in existing:
            params["hostmacroid"] = existing[name]
            zabbix.api("usermacro.update", params)
        else:
            params["hostid"] = host_id
            zabbix.api("usermacro.create", params)

    item_ids = {}

    def item(key, name, properties):
        params = {"hostid": host_id, "key_": key, "name": name, "status": 0,
                  "history": "1h", "trends": "0", **properties}
        found = zabbix.api("item.get", {
            "hostids": [host_id], "filter": {"key_": key}, "output": ["itemid"],
        })
        if found:
            params["itemid"] = found[0]["itemid"]
            zabbix.api("item.update", params)
            item_ids[key] = found[0]["itemid"]
        else:
            item_ids[key] = zabbix.api("item.create", params)["itemids"][0]
        return item_ids[key]

    def http(url, preprocessing):
        return {"type": 19, "value_type": 4, "delay": "4s", "url": url,
                "request_method": 0, "retrieve_mode": 0, "status_codes": "200",
                "timeout": "10s", "verify_peer": 1, "verify_host": 1,
                "follow_redirects": 0, "headers": [
                    {"name": "Authorization", "value": "Bearer {$BBB.AAP.TOKEN}"},
                    {"name": "Accept", "value": "application/json"},
                ], "preprocessing": preprocessing}

    stream_id = item("aap.demo.stream.summary", "AAP Event Stream summary", http(
        "{$BBB.AAP.URL}/api/eda/v1/event-streams/{$BBB.AAP.STREAM_ID}/",
        javascript("stream_summary.js"),
    ))
    events_id = item("aap.demo.stream.events_received", "Events received by EDA", {
        "type": 18, "value_type": 3, "delay": "0", "master_itemid": stream_id,
        "history": "31d", "trends": "365d", "preprocessing": jsonpath("$.events_received"),
    })
    jobs_url = ("{$BBB.AAP.URL}/api/controller/v2/jobs/"
                "?job_template__in={$BBB.AAP.JOB_TEMPLATES}&order_by=-id&page_size=5")
    recent_id = item("aap.demo.jobs.recent", "AAP recent demo job summary", http(
        jobs_url, javascript("jobs_summary.js"),
    ))
    recent_table_id = item("aap.demo.jobs.recent_table", "Recent Big Bad Button jobs", {
        "type": 18, "value_type": 4, "delay": "0", "master_itemid": recent_id,
        "preprocessing": javascript("jobs_table.js"),
    })
    running_id = item("aap.demo.jobs.running", "AAP running demo job summary", http(
        jobs_url + "&status=running", javascript("jobs_summary.js"),
    ))
    running_count_id = item("aap.demo.jobs.running_count", "Big Bad Button jobs running", {
        "type": 18, "value_type": 3, "delay": "0", "master_itemid": running_id,
        "history": "31d", "trends": "365d", "preprocessing": jsonpath("$.count"),
    })
    running_table_id = item("aap.demo.jobs.running_table", "Currently running Big Bad Button jobs", {
        "type": 18, "value_type": 4, "delay": "0", "master_itemid": running_id,
        "preprocessing": javascript("jobs_table.js"),
    })

    variables = dict(settings, demo_aap_events_item_id=events_id,
                     demo_aap_running_count_item_id=running_count_id,
                     demo_aap_recent_jobs_item_id=recent_table_id,
                     demo_aap_running_jobs_item_id=running_table_id,
                     demo_zabbix_website_map_id=settings["demo_zabbix_website_map_id"])
    text = (ROOT / "assets" / "zabbix" / "website-deliveries-dashboard.json.j2").read_text()
    for key, value in variables.items():
        text = text.replace("{{ " + key + " }}", str(value))
    if "{{" in text:
        raise RuntimeError("Dashboard template has unfilled placeholders")
    desired = json.loads(text)
    dashboard_id = str(settings["demo_zabbix_demo_dashboard_id"])
    dashboard = zabbix.api("dashboard.get", {
        "dashboardids": [dashboard_id], "output": "extend", "selectPages": "extend",
    })[0]
    if dashboard["name"] != desired["name"] or len(dashboard["pages"]) != 1:
        raise RuntimeError("Dashboard identity or page structure does not match")
    page = dashboard["pages"][0]
    existing_widgets = {widget["name"]: widget for widget in page["widgets"]}
    desired_widgets = desired["pages"][0]["widgets"]
    if set(existing_widgets) - {widget["name"] for widget in desired_widgets}:
        raise RuntimeError("Dashboard has additional widgets; preserve them before updating")
    for widget in desired_widgets:
        if widget["name"] in existing_widgets:
            widget["widgetid"] = existing_widgets[widget["name"]]["widgetid"]
    zabbix.api("dashboard.update", {
        "dashboardid": dashboard_id,
        "pages": [{"dashboard_pageid": page["dashboard_pageid"], "name": page["name"],
                   "display_period": page["display_period"], "widgets": desired_widgets}],
    })
    after = zabbix.api("dashboard.get", {
        "dashboardids": [dashboard_id], "output": "extend", "selectPages": "extend",
    })[0]
    for field in ("name", "userid", "private"):
        if dashboard[field] != after[field]:
            raise RuntimeError("Dashboard access setting changed")
    actual_widgets = {widget["name"]: widget for widget in after["pages"][0]["widgets"]}
    for widget in desired_widgets:
        actual = actual_widgets[widget["name"]]
        for field in ("type", "x", "y", "width", "height"):
            if str(widget[field]) != str(actual[field]):
                raise RuntimeError("Widget layout readback failed")
        fields = {field["name"]: str(field["value"]) for field in actual["fields"]}
        for field in widget["fields"]:
            if fields.get(field["name"]) != str(field["value"]):
                raise RuntimeError("Widget field readback failed")
    return {"host_id": host_id, "item_ids": item_ids, "dashboard_id": dashboard_id,
            "widgets": len(actual_widgets), "configuration_verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vars-file", type=Path, default=ROOT / "myvars")
    parser.add_argument("--vault-password-file", type=Path, required=True)
    args = parser.parse_args()
    settings = load_settings(args.vars_file, args.vault_password_file)
    print(json.dumps(configure(settings)))


if __name__ == "__main__":
    main()
