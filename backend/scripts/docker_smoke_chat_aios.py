"""Smoke: attachment upload + AIOS compile/deploy against live Docker API."""
from __future__ import annotations

import base64
import io
import json
import sys
import urllib.error
import urllib.request

import rsa

BASE = "http://127.0.0.1:3001"


def req(method: str, path: str, data=None, headers=None, files=None):
    headers = dict(headers or {})
    if files:
        boundary = "----NovaFlowBoundary7MA4YWxkTrZu0gW"
        body = b""
        for name, (filename, content, ctype) in files.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            body += f"Content-Type: {ctype}\r\n\r\n".encode()
            body += content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        payload = body
    elif data is not None:
        payload = json.dumps(data).encode()
        headers.setdefault("Content-Type", "application/json")
    else:
        payload = None
    r = urllib.request.Request(BASE + path, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main():
    health = req("GET", "/health")
    assert health["status_code"] == 200, health
    print("health ok")

    pk = req("GET", "/api/v1/user/public_key")
    pem = pk["data"]["public_key"]
    pub = rsa.PublicKey.load_pkcs1(pem.encode() if isinstance(pem, str) else pem)
    import os
    pwd = (os.getenv("NOVAFLOW_ADMIN_PASSWORD") or "").encode()
    if not pwd:
        raise SystemExit("Set NOVAFLOW_ADMIN_PASSWORD for smoke login")
    enc = base64.b64encode(rsa.encrypt(pwd, pub)).decode()
    login = req("POST", "/api/v1/user/login", {"user_name": "admin", "password": enc})
    token = login["data"]["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    print("login ok")

    conv = req("POST", "/api/v1/conversations", {"title": "Docker smoke", "conversation_type": "assistant"}, headers=h)
    cid = conv["data"]["id"]
    print("conversation", cid)

    up = req(
        "POST",
        f"/api/v1/conversations/{cid}/attachments",
        headers=h,
        files={"file": ("notes.txt", b"menu item pizza price 12", "text/plain")},
    )
    assert up["status_code"] == 200, up
    assert up["data"]["attachment_id"], up
    print("upload ok", up["data"]["attachment_id"])

    compiled = req(
        "POST",
        "/api/v1/aios/project",
        {"goal": "Build workflow automation for restaurant telegram bot"},
        headers=h,
    )
    assert compiled["status_code"] == 200, compiled
    sid = compiled["data"]["solution_id"]
    pid = compiled["data"]["project_id"]
    print("compiled", sid, "project", pid)

    # deploy via kernel endpoint
    deployed = req("POST", f"/api/v1/aios/project/{pid}/deploy", {}, headers=h)
    assert deployed["status_code"] == 200, deployed
    data = deployed["data"]
    assert data.get("workflow_id"), data
    print("deployed workflow", data["workflow_id"], "agent", data.get("agent_id"))
    print("SMOKE_OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("SMOKE_FAIL", exc)
        sys.exit(1)
