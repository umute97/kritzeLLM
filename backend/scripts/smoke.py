"""Smoke-tests a running stack: uploads a page and waits for its ingest job to finish.

Standard library only, so it runs anywhere: `python3 backend/scripts/smoke.py`.
Reads `API_PORT` (default 8000) and `API_TOKEN` (if the server needs one) from the environment.
"""

import json
import os
import struct
import sys
import time
import urllib.request
import uuid
import zlib
from typing import Any

BASE = f"http://localhost:{os.environ.get('API_PORT') or 8000}/api/v1"
TIMEOUT_SECONDS = 30


def _png(width: int = 64, height: int = 48) -> bytes:
    """A solid PNG in a random color, so every run uploads a new page."""
    color = os.urandom(3)
    rows = b"".join(b"\x00" + color * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _request(method: str, path: str, body: bytes | None = None, content_type: str = "") -> Any:
    request = urllib.request.Request(BASE + path, data=body, method=method)
    if content_type:
        request.add_header("Content-Type", content_type)
    if token := os.environ.get("API_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response) if response.status != 204 else None


def _upload(journal_id: str, filename: str, data: bytes) -> dict[str, Any]:
    boundary = uuid.uuid4().hex
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode()
        + data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    result = _request(
        "POST", f"/journals/{journal_id}/pages", body, f"multipart/form-data; boundary={boundary}"
    )
    return result["items"][0]


def main() -> int:
    journal = _request(
        "POST", "/journals", json.dumps({"name": "Smoke test"}).encode(), "application/json"
    )
    item = _upload(journal["id"], "smoke.png", _png())
    job = item["job"]
    print(f"Uploaded page {item['page']['id']}, job {job['id']} is {job['status']}")

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while job["status"] in ("queued", "running"):
        if time.monotonic() > deadline:
            print(
                f"Job {job['id']} still {job['status']} after {TIMEOUT_SECONDS}s. Is the worker up?"
            )
            return 1
        time.sleep(0.5)
        job = _request("GET", f"/jobs/{job['id']}")

    page = _request("GET", f"/pages/{item['page']['id']}")
    listed = any(each["id"] == job["id"] for each in _request("GET", "/jobs?limit=100")["items"])
    print(f"Job {job['status']}, page {page['status']}, listed in /jobs: {listed}")
    _request("DELETE", f"/journals/{journal['id']}")  # Takes the page and its job along.
    return 0 if job["status"] == "succeeded" and page["status"] == "ready" and listed else 1


if __name__ == "__main__":
    sys.exit(main())
