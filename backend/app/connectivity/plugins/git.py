"""Production Git connector plugin.

Uses the system `git` binary via async subprocess for real clone/list/read.
Credentials (PAT) are injected into the HTTPS remote URL. All operations run in
an isolated temp directory and are cleaned up afterwards.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy.orm import Session

from app.connectivity.plugins.base import BaseConnectorPlugin, PluginResult
from app.database import ConnectorConnection, ConnectorSyncJob


def _config(conn: ConnectorConnection) -> dict[str, Any]:
    try:
        return json.loads(conn.config_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _authed_url(repo_url: str, token: str) -> str:
    if not token or not repo_url.startswith("https://"):
        return repo_url
    parsed = urlparse(repo_url)
    netloc = f"x-access-token:{token}@{parsed.netloc}"
    return urlunparse(parsed._replace(netloc=netloc))


async def _run_git(*args: str, cwd: str | None = None, timeout: int = 90) -> tuple[int, str, str]:
    if not shutil.which("git"):
        raise RuntimeError("git binary not available on host")
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("git operation timed out")
    return proc.returncode or 0, out.decode(errors="ignore"), err.decode(errors="ignore")


class GitPlugin(BaseConnectorPlugin):
    connector_type = "git"
    description = "Git repository (clone, list, read via system git)"

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        cfg = _config(conn)
        if not cfg.get("repo_url"):
            return PluginResult(success=False, message="repo_url not configured")
        if not shutil.which("git"):
            return PluginResult(success=False, message="git binary not available on host")
        return PluginResult(success=True, message="git available; verify reachability via list_files")

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        params = params or {}
        cfg = _config(conn)
        repo_url = params.get("repo_url") or cfg.get("repo_url") or ""
        if not repo_url:
            return PluginResult(success=False, message="repo_url required")
        branch = params.get("branch") or cfg.get("branch") or ""
        url = _authed_url(repo_url, secret)
        try:
            if action in ("test", "verify"):
                code, _out, err = await _run_git("ls-remote", "--heads", url, timeout=45)
                return PluginResult(success=code == 0, message="reachable" if code == 0 else err[:200])
            if action in ("list_files", "get_file", "sync"):
                tmp = tempfile.mkdtemp(prefix="nf_git_")
                try:
                    clone_args = ["clone", "--depth", "1", "--quiet"]
                    if branch:
                        clone_args += ["--branch", branch]
                    clone_args += [url, tmp]
                    code, _out, err = await _run_git(*clone_args, timeout=120)
                    if code != 0:
                        return PluginResult(success=False, message=f"clone failed: {err[:200]}")
                    root = Path(tmp)
                    if action == "get_file":
                        rel = (params.get("path") or "").lstrip("/")
                        target = root / rel
                        if not rel or not target.is_file() or root not in target.resolve().parents:
                            return PluginResult(success=False, message="file not found")
                        text = target.read_text(encoding="utf-8", errors="ignore")[:200000]
                        return PluginResult(success=True, message="file read", data={"path": rel, "content": text})
                    files = [
                        p.relative_to(root).as_posix()
                        for p in sorted(root.rglob("*"))
                        if p.is_file() and ".git/" not in p.relative_to(root).as_posix()
                    ][:1000]
                    return PluginResult(success=True, message=f"{len(files)} files", data={"files": files}, checkpoint={"file_count": len(files)})
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"Git error: {exc}")

    def sync(self, db: Session, conn: ConnectorConnection, job: ConnectorSyncJob) -> dict[str, Any]:
        return PluginResult(success=True, message="Use invoke_action('list_files'/'get_file') for git sync", checkpoint={}).to_dict()
