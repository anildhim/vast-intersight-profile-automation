#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from intersight_upsert import request_json


def first_result_or_none(response):
    results = response.get("Results") or []
    return results[0] if results else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--policy-file", required=True)
    parser.add_argument("--policy-organization-moid", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--role-moid", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    policy_payload = json.loads(Path(args.policy_file).read_text())
    policy_name = policy_payload["Name"]

    _, policy_lookup = request_json(
        api_uri=args.api_uri,
        resource_path="/iam/EndPointUserPolicies",
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        query={"$filter": f"Name eq '{policy_name}'"},
    )
    policy_results = policy_lookup.get("Results") or []
    filtered_policy_results = [
        item for item in policy_results
        if (item.get("Organization") or {}).get("Moid") == args.policy_organization_moid
    ]
    policy_obj = filtered_policy_results[0] if filtered_policy_results else None

    if policy_obj:
        policy_moid = policy_obj["Moid"]
        patch_payload = dict(policy_payload)
        patch_payload.pop("Organization", None)
        _, policy_response = request_json(
            api_uri=args.api_uri,
            resource_path=f"/iam/EndPointUserPolicies/{policy_moid}",
            method="PATCH",
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            body=patch_payload,
        )
        policy_action = "patch"
    else:
        _, policy_response = request_json(
            api_uri=args.api_uri,
            resource_path="/iam/EndPointUserPolicies",
            method="POST",
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            body=policy_payload,
        )
        policy_moid = policy_response["Moid"]
        policy_action = "post"

    _, user_lookup = request_json(
        api_uri=args.api_uri,
        resource_path="/iam/EndPointUsers",
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        query={"$filter": f"Name eq '{args.username}'"},
    )
    user_results = user_lookup.get("Results") or []
    filtered_user_results = [
        item for item in user_results
        if (item.get("Organization") or {}).get("Moid") == args.policy_organization_moid
    ]
    user_obj = filtered_user_results[0] if filtered_user_results else None
    if not user_obj:
        user_payload = {
            "Name": args.username,
            "ObjectType": "iam.EndPointUser",
            "ClassId": "iam.EndPointUser",
            "Organization": {
                "ObjectType": "organization.Organization",
                "ClassId": "mo.MoRef",
                "Moid": args.policy_organization_moid,
            },
        }
        _, user_obj = request_json(
            api_uri=args.api_uri,
            resource_path="/iam/EndPointUsers",
            method="POST",
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            body=user_payload,
        )

    role_payload = {
        "Password": args.password,
        "Enabled": True,
        "EndPointRole": [
            {
                "ObjectType": "iam.EndPointRole",
                "ClassId": "mo.MoRef",
                "Moid": args.role_moid,
            }
        ],
        "EndPointUser": {
            "ObjectType": "iam.EndPointUser",
            "ClassId": "mo.MoRef",
            "Moid": user_obj["Moid"],
        },
        "EndPointUserPolicy": {
            "ObjectType": "iam.EndPointUserPolicy",
            "ClassId": "mo.MoRef",
            "Moid": policy_moid,
        },
    }

    _, role_lookup = request_json(
        api_uri=args.api_uri,
        resource_path="/iam/EndPointUserRoles",
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        query={"$filter": f"EndPointUserPolicy.Moid eq '{policy_moid}'"},
    )
    role_obj = first_result_or_none(role_lookup)

    if role_obj:
        _, role_response = request_json(
            api_uri=args.api_uri,
            resource_path=f"/iam/EndPointUserRoles/{role_obj['Moid']}",
            method="PATCH",
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            body=role_payload,
        )
        role_action = "patch"
    else:
        _, role_response = request_json(
            api_uri=args.api_uri,
            resource_path="/iam/EndPointUserRoles",
            method="POST",
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            body=role_payload,
        )
        role_action = "post"

    print(
        json.dumps(
            {
                "changed": True,
                "policy_action": policy_action,
                "policy_response": policy_response,
                "role_action": role_action,
                "role_response": role_response,
            }
        )
    )


if __name__ == "__main__":
    main()
