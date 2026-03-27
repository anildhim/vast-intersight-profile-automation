#!/usr/bin/env python3
"""Derive one or more Intersight server profiles from a template."""

from __future__ import annotations

import argparse
import json
import re
import sys

from intersight_upsert import request_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--template-moid", required=True)
    parser.add_argument("--organization-moid", required=True)
    parser.add_argument("--base-name", required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--auto-start-index", action="store_true")
    parser.add_argument("--serial-numbers-json", default="[]")
    parser.add_argument("--description", default="")
    parser.add_argument("--tags-json", default="[]")
    return parser.parse_args()


def lookup_profile(api_uri: str, api_key_id: str, api_private_key: str, name: str, organization_moid: str):
    filter_expr = f"Name eq '{name}' and Organization/Moid eq '{organization_moid}'"
    _, response = request_json(
        api_uri=api_uri,
        resource_path="/server/Profiles",
        method="GET",
        api_key_id=api_key_id,
        api_private_key=api_private_key,
        query={"$filter": filter_expr},
    )
    results = response.get("Results", [])
    return results[0] if results else None


def determine_start_index(
    api_uri: str,
    api_key_id: str,
    api_private_key: str,
    base_name: str,
    organization_moid: str,
) -> int:
    _, response = request_json(
        api_uri=api_uri,
        resource_path="/server/Profiles",
        method="GET",
        api_key_id=api_key_id,
        api_private_key=api_private_key,
        query={"$filter": f"Organization/Moid eq '{organization_moid}'"},
    )
    pattern = re.compile(rf"^{re.escape(base_name)}_DERIVED-(\d+)$")
    highest = 0
    for item in response.get("Results", []):
        match = pattern.match(item.get("Name", ""))
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1 if highest else 1


def build_target_profile_names(args: argparse.Namespace) -> list[str]:
    serial_numbers = json.loads(args.serial_numbers_json)
    if not isinstance(serial_numbers, list):
        raise SystemExit("--serial-numbers-json must decode to a JSON list")
    if any(not isinstance(item, str) or not item.strip() for item in serial_numbers):
        raise SystemExit("Each serial number must be a non-empty string")

    normalized_serial_numbers = [item.strip() for item in serial_numbers]
    if normalized_serial_numbers:
        if args.auto_start_index:
            raise SystemExit("--auto-start-index cannot be used with serial-based naming")
        if args.start_index != 1:
            raise SystemExit("--start-index must remain 1 when using serial-based naming")
        if args.count != len(normalized_serial_numbers):
            raise SystemExit("--count must match the number of serial numbers when using serial-based naming")
        return [f"{args.base_name}_{serial_number}" for serial_number in normalized_serial_numbers]

    if args.auto_start_index:
        args.start_index = determine_start_index(
            api_uri=args.api_uri,
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            base_name=args.base_name,
            organization_moid=args.organization_moid,
        )

    return [
        f"{args.base_name}_DERIVED-{index}"
        for index in range(args.start_index, args.start_index + args.count)
    ]


def main() -> None:
    args = parse_args()
    tags = json.loads(args.tags_json)
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if args.start_index < 1:
        raise SystemExit("--start-index must be at least 1")

    existing = []
    missing_targets = []
    target_profile_names = build_target_profile_names(args)
    for profile_name in target_profile_names:
        current = lookup_profile(
            api_uri=args.api_uri,
            api_key_id=args.api_key_id,
            api_private_key=args.api_private_key,
            name=profile_name,
            organization_moid=args.organization_moid,
        )
        if current:
            existing.append({"name": profile_name, "moid": current["Moid"]})
            continue

        missing_targets.append(
            {
                "Name": profile_name,
                "Description": args.description,
                "ObjectType": "server.Profile",
                "Organization": {
                    "Moid": args.organization_moid,
                    "ObjectType": "organization.Organization",
                },
                "Tags": tags,
            }
        )

    result = {
        "changed": bool(missing_targets),
        "existing_profiles": existing,
        "created_count": len(missing_targets),
        "start_index": args.start_index,
        "target_profile_names": target_profile_names,
        "created_profile_names": [item["Name"] for item in missing_targets],
    }

    if not missing_targets:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
        return

    payload = {
        "ObjectType": "bulk.MoCloner",
        "ClassId": "bulk.MoCloner",
        "Sources": [
            {
                "Moid": args.template_moid,
                "ObjectType": "server.ProfileTemplate",
            }
        ],
        "Targets": missing_targets,
        "WorkflowNameSuffix": "Derive Server Profile from a Template",
        "Organization": {
            "Moid": args.organization_moid,
            "ObjectType": "organization.Organization",
        },
    }

    _, response = request_json(
        api_uri=args.api_uri,
        resource_path="/bulk/MoCloners",
        method="POST",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        body=payload,
    )
    result["response"] = response
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
