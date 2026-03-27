#!/usr/bin/env python3

import argparse
import json
import sys

from intersight_upsert import request_json


TERMINAL_DEPLOY_STATUSES = {"Complete", "Failed", "Error"}
TERMINAL_CONFIG_STATES = {"Failed", "Error"}
SUCCESS_CONFIG_STATES = {"Associated"}
SUCCESS_CONTROL_ACTIONS = {"No-op", ""}


def lookup_profile(api_uri, api_key_id, api_private_key, profile_name, organization_moid):
    _, response = request_json(
        api_uri=api_uri,
        resource_path="/server/Profiles",
        method="GET",
        api_key_id=api_key_id,
        api_private_key=api_private_key,
        query={"$filter": f"Name eq '{profile_name}'"},
    )
    results = [
        item
        for item in (response.get("Results") or [])
        if ((item.get("Organization") or {}).get("Moid") == organization_moid)
    ]
    if not results:
        raise RuntimeError(
            f"No server profile found for name={profile_name} organization_moid={organization_moid}"
        )
    if len(results) > 1:
        raise RuntimeError(
            f"Multiple server profiles found for name={profile_name} organization_moid={organization_moid}"
        )
    return results[0]


def lookup_server_serial(api_uri, api_key_id, api_private_key, assigned_server_moid):
    if not assigned_server_moid:
        return ""
    _, response = request_json(
        api_uri=api_uri,
        resource_path=f"/compute/PhysicalSummaries/{assigned_server_moid}",
        method="GET",
        api_key_id=api_key_id,
        api_private_key=api_private_key,
    )
    return response.get("Serial", "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--profile-name", required=True)
    parser.add_argument("--organization-moid", required=True)
    args = parser.parse_args()

    profile = lookup_profile(
        api_uri=args.api_uri,
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        profile_name=args.profile_name,
        organization_moid=args.organization_moid,
    )

    deploy_status = profile.get("DeployStatus", "")
    config_context = profile.get("ConfigContext") or {}
    config_state = config_context.get("ConfigState", "")
    control_action = config_context.get("ControlAction", "")
    scheduled_actions = profile.get("ScheduledActions") or []
    assigned_server = profile.get("AssignedServer") or {}
    server_serial_number = lookup_server_serial(
        api_uri=args.api_uri,
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        assigned_server_moid=assigned_server.get("Moid", ""),
    )

    success = (
        deploy_status == "Complete"
        and config_state in SUCCESS_CONFIG_STATES
        and control_action in SUCCESS_CONTROL_ACTIONS
    )
    failure = (
        deploy_status in {"Failed", "Error"}
        or config_state in TERMINAL_CONFIG_STATES
    )
    terminal = success or failure
    status = deploy_status or config_state or control_action or "Unknown"

    print(
        json.dumps(
            {
                "profile_name": profile.get("Name", args.profile_name),
                "status": status,
                "deploy_status": deploy_status,
                "config_state": config_state,
                "control_action": control_action,
                "server_serial_number": server_serial_number,
                "assigned_server_moid": assigned_server.get("Moid", ""),
                "scheduled_actions": [item.get("Action", "") for item in scheduled_actions],
                "terminal": terminal,
                "success": success,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
