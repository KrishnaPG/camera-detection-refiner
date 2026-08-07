#!/usr/bin/env python3
"""Download all objects from an S3-compatible bucket using AWS SigV4."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple


SERVICE = "s3"
REGION = "auto"


class ObjectInfo(NamedTuple):
    key: str
    size: int


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signature_key(secret: str, date_stamp: str) -> bytes:
    key_date = _sign(("AWS4" + secret).encode("utf-8"), date_stamp)
    key_region = _sign(key_date, REGION)
    key_service = _sign(key_region, SERVICE)
    return _sign(key_service, "aws4_request")


def _canonical_query(params: dict[str, str]) -> str:
    pairs = []
    for key, value in sorted(params.items()):
        pairs.append(
            f"{urllib.parse.quote(key, safe='-_.~')}="
            f"{urllib.parse.quote(value, safe='-_.~')}"
        )
    return "&".join(pairs)


def _build_request(
    endpoint: str,
    access_key: str,
    secret_key: str,
    method: str,
    path: str,
    params: dict[str, str] | None = None,
) -> bytes:
    params = params or {}
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    timestamp = dt.datetime.now(dt.UTC)
    amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = timestamp.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(b"").hexdigest()

    canonical_uri = urllib.parse.quote(path, safe="/-_.~")
    canonical_query = _canonical_query(params)
    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            method,
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    credential_scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        _signature_key(secret_key, date_stamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    url = urllib.parse.urlunparse(
        (parsed.scheme, host, canonical_uri, "", canonical_query, "")
    )
    return urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": authorization,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        },
    )


def _request(
    endpoint: str,
    access_key: str,
    secret_key: str,
    method: str,
    path: str,
    params: dict[str, str] | None = None,
) -> bytes:
    request = _build_request(endpoint, access_key, secret_key, method, path, params)
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _download_to_file(
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    key: str,
    destination: Path,
) -> int:
    request = _build_request(endpoint, access_key, secret_key, "GET", f"/{bucket}/{key}")
    bytes_written = 0
    with urllib.request.urlopen(request, timeout=120) as response:
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                bytes_written += len(chunk)
    return bytes_written


def _list_objects(
    endpoint: str, access_key: str, secret_key: str, bucket: str
) -> list[ObjectInfo]:
    objects: list[ObjectInfo] = []
    token: str | None = None
    while True:
        params = {"list-type": "2"}
        if token:
            params["continuation-token"] = token
        body = _request(endpoint, access_key, secret_key, "GET", f"/{bucket}", params)
        root = ET.fromstring(body)
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}", 1)[0] + "}"
        for item in root.findall(f"{namespace}Contents"):
            key = item.findtext(f"{namespace}Key")
            size = item.findtext(f"{namespace}Size")
            if key:
                objects.append(ObjectInfo(key=key, size=int(size or "0")))
        truncated = root.findtext(f"{namespace}IsTruncated") == "true"
        token = root.findtext(f"{namespace}NextContinuationToken")
        if not truncated:
            return objects


def main() -> int:
    endpoint = _env("R2_ENDPOINT").rstrip("/")
    access_key = _env("R2_ACCESS_KEY_ID")
    secret_key = _env("R2_SECRET_ACCESS_KEY")
    bucket = _env("R2_BUCKET")
    output_dir = Path(os.environ.get("R2_OUTPUT_DIR", "data"))
    output_dir.mkdir(parents=True, exist_ok=True)

    objects = _list_objects(endpoint, access_key, secret_key, bucket)
    if not objects:
        print("No objects found.")
        return 0

    downloaded = 0
    skipped = 0
    for obj in objects:
        key = obj.key
        destination = output_dir / key
        if destination.name == "":
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.stat().st_size == obj.size:
            skipped += 1
            print(f"Skipped {key} ({obj.size} bytes)", flush=True)
            continue
        bytes_written = _download_to_file(
            endpoint, access_key, secret_key, bucket, key, destination
        )
        downloaded += 1
        print(f"Downloaded {key} ({bytes_written} bytes)", flush=True)

    print(
        f"Downloaded {downloaded} object(s), skipped {skipped} existing object(s) "
        f"into {output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
