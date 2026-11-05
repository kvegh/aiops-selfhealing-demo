#!/usr/bin/env python3
"""Deny another repair target or SSH host in this one demo invocation."""

import json
import os
import sys


def check(request, repair_id, alias, allowed_names=None):
    if not isinstance(request, dict) or not repair_id.isascii() or not repair_id.isdigit() or int(repair_id) <= 0 or not alias:
        return False
    name, arguments = request.get("tool_name"), request.get("tool_input")
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return False
    if allowed_names is not None and name not in allowed_names:
        return False
    if name == "mcp__aap-mcp__job_templates_launch_create":
        identity = arguments.get("id")
        return (type(identity) in (str, int) and str(identity) == repair_id
                and set(arguments) <= {"id", "requestBody"}
                and arguments.get("requestBody") in (None, {}))
    if name.startswith("mcp__linux-mcp__"):
        return arguments.get("host") == alias
    # Returning normally does not grant permission or bypass other hooks.
    return True


def main():
    try:
        text = sys.stdin.read(131073)
        allowed = len(text) <= 131072 and check(json.loads(text),
            os.environ.get("AIOPS_ALLOWED_REPAIR_JT_ID", ""),
            os.environ.get("AIOPS_ALLOWED_LINUX_HOST", ""),
            set(os.environ.get("AIOPS_ALLOWED_TOOL_NAMES", "").split(",")))
    except (ValueError, TypeError, KeyError):
        allowed = False
    if not allowed:
        print("The request does not match this job's verified repair template or testserver alias.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
