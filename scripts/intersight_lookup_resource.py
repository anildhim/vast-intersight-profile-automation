#!/usr/bin/env python3

import argparse
import json
import sys

from intersight_upsert import request_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--resource-path", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--organization-moid", default="")
    args = parser.parse_args()

    _, response = request_json(
        api_uri=args.api_uri,
        resource_path=args.resource_path,
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        query={"$filter": f"Name eq '{args.name}'"},
    )

    results = response.get("Results") or []
    if args.organization_moid:
        results = [
            item for item in results
            if (item.get("Organization") or {}).get("Moid") == args.organization_moid
        ]

    if not results:
        raise RuntimeError(
            f"No resource found for name={args.name} "
            f"resource_path={args.resource_path} organization_moid={args.organization_moid}"
        )

    if len(results) > 1:
        raise RuntimeError(
            f"Multiple resources found for name={args.name} "
            f"resource_path={args.resource_path} organization_moid={args.organization_moid}"
        )

    print(json.dumps(results[0]))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
