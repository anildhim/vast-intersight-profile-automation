#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from intersight_upsert import request_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--shared-resource-moid", required=True)
    parser.add_argument("--shared-with-resource-moid", required=True)
    args = parser.parse_args()

    _, existing = request_json(
        api_uri=args.api_uri,
        resource_path="/iam/SharingRules",
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
    )

    for item in existing.get("Results") or []:
        shared_resource = (item.get("SharedResource") or {}).get("Moid")
        shared_with = (item.get("SharedWithResource") or {}).get("Moid")
        if (
            shared_resource == args.shared_resource_moid
            and shared_with == args.shared_with_resource_moid
        ):
            print(json.dumps({"changed": False, "action": "noop", "response": item}))
            return

    payload = {
        "SharedResource": {
            "ObjectType": "organization.Organization",
            "ClassId": "mo.MoRef",
            "Moid": args.shared_resource_moid,
        },
        "SharedWithResource": {
            "ObjectType": "organization.Organization",
            "ClassId": "mo.MoRef",
            "Moid": args.shared_with_resource_moid,
        },
    }

    _, response = request_json(
        api_uri=args.api_uri,
        resource_path="/iam/SharingRules",
        method="POST",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        body=payload,
    )
    print(json.dumps({"changed": True, "action": "post", "response": response}))


if __name__ == "__main__":
    main()
