#!/usr/bin/env python3

import argparse
import json
import sys

from intersight_upsert import request_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--serial-number", required=True)
    args = parser.parse_args()

    _, response = request_json(
        api_uri=args.api_uri,
        resource_path="/compute/PhysicalSummaries",
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        query={"$filter": f"Serial eq '{args.serial_number}'"},
    )

    results = response.get("Results") or []
    if not results:
        raise RuntimeError(f"No server found for serial_number={args.serial_number}")
    if len(results) > 1:
        raise RuntimeError(f"Multiple servers found for serial_number={args.serial_number}")

    print(json.dumps(results[0]))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
