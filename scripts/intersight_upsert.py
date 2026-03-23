#!/usr/bin/env python3

import argparse
import base64
import hashlib
import json
from email.utils import formatdate
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding


def sha256_b64(data: str) -> str:
    return base64.b64encode(hashlib.sha256(data.encode()).digest()).decode("ascii")


def load_key(path: str):
    pem = Path(path).read_text()
    header = pem.splitlines()[0].strip().replace("-----BEGIN ", "").replace("-----", "")
    key = serialization.load_pem_private_key(pem.encode(), None, default_backend())
    return header, key


def sign_string(header: str, key, message: str):
    if header == "RSA PRIVATE KEY":
        sig = key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
        alg = "rsa-sha256"
    elif header == "EC PRIVATE KEY":
        sig = key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        alg = "hs2019"
    else:
        raise ValueError(f"Unsupported key header: {header}")
    return base64.b64encode(sig).decode("ascii"), alg


def request_json(api_uri: str, resource_path: str, method: str, api_key_id: str, api_private_key: str, body=None, query=None):
    host = urlparse(api_uri).netloc
    base_path = urlparse(api_uri).path
    query_str = ("?" + urlencode(query)) if query else ""
    path = f"{resource_path}{query_str}"
    body_string = "" if method == "GET" else json.dumps(body)
    body_digest = sha256_b64(body_string)
    date_hdr = formatdate(timeval=None, localtime=False, usegmt=True)
    request_target = f"{method.lower()} {base_path}{path}"

    signing_headers = {
        "Host": host,
        "Date": date_hdr,
        "Digest": f"SHA-256={body_digest}",
    }
    signing_string = "\n".join(
        ["(request-target): " + request_target]
        + [f"{k.lower()}: {v}" for k, v in signing_headers.items()]
    )

    key_header, key = load_key(api_private_key)
    signature, algorithm = sign_string(key_header, key, signing_string)
    auth = (
        f'Signature keyId="{api_key_id}",'
        f'algorithm="{algorithm}",'
        f'headers="(request-target) host date digest",'
        f'signature="{signature}"'
    )

    req = Request(
        api_uri + path,
        data=None if method == "GET" else body_string.encode(),
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Host": host,
            "Date": date_hdr,
            "Digest": f"SHA-256={body_digest}",
            "Authorization": auth,
        },
    )

    try:
        with urlopen(req) as resp:
            content = resp.read().decode()
            return resp.status, json.loads(content) if content else {}
    except HTTPError as err:
        content = err.read().decode()
        raise RuntimeError(f"HTTP {err.code}: {content}") from err


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-uri", required=True)
    parser.add_argument("--resource-path", required=True)
    parser.add_argument("--api-key-id", required=True)
    parser.add_argument("--api-private-key", required=True)
    parser.add_argument("--payload-file", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--organization-moid", default="")
    args = parser.parse_args()

    payload = json.loads(Path(args.payload_file).read_text())
    _, existing = request_json(
        api_uri=args.api_uri,
        resource_path=args.resource_path,
        method="GET",
        api_key_id=args.api_key_id,
        api_private_key=args.api_private_key,
        query={"$filter": f"Name eq '{args.name}'"},
    )
    results = existing.get("Results") or []
    if args.organization_moid:
        results = [
            item for item in results
            if (item.get("Organization") or {}).get("Moid") == args.organization_moid
        ]
    if results:
      moid = results[0]["Moid"]
      _, response = request_json(
          api_uri=args.api_uri,
          resource_path=f"{args.resource_path}/{moid}",
          method="PATCH",
          api_key_id=args.api_key_id,
          api_private_key=args.api_private_key,
          body=payload,
      )
      print(json.dumps({"changed": True, "action": "patch", "response": response}))
    else:
      _, response = request_json(
          api_uri=args.api_uri,
          resource_path=args.resource_path,
          method="POST",
          api_key_id=args.api_key_id,
          api_private_key=args.api_private_key,
          body=payload,
      )
      print(json.dumps({"changed": True, "action": "post", "response": response}))


if __name__ == "__main__":
    main()
