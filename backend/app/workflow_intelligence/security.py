"""Workflow security validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.security.ai_guard import detect_prompt_injection
from app.workflow_intelligence.graph.model import WorkflowGraph


@dataclass
class SecurityFinding:
    code: str
    severity: str
    message: str
    node_id: str = ""


@dataclass
class SecurityReport:
    ok: bool
    findings: list[SecurityFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "findings": [
                {"code": f.code, "severity": f.severity, "message": f.message, "node_id": f.node_id}
                for f in self.findings
            ],
        }


_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}", re.I),
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]{20,}", re.I),
]


def validate_workflow_security(graph: WorkflowGraph) -> SecurityReport:
    findings: list[SecurityFinding] = []

    for n in graph.nodes:
        data = n.data or {}
        blob = " ".join(str(v) for v in data.values())

        inj = detect_prompt_injection(blob)
        if inj:
            findings.append(
                SecurityFinding("prompt_injection_risk", "warning", inj, node_id=n.id)
            )

        for pat in _SECRET_PATTERNS:
            if pat.search(blob):
                findings.append(
                    SecurityFinding(
                        "credential_exposure",
                        "error",
                        "Possible secret embedded in node configuration",
                        node_id=n.id,
                    )
                )
                break

        if n.type == "http":
            url = str(data.get("url") or "")
            if url.startswith("http://") and "{{" not in url:
                findings.append(
                    SecurityFinding("insecure_http", "warning", "Plain HTTP URL detected", node_id=n.id)
                )
            if any(h in url.lower() for h in ("169.254.", "127.0.0.1", "localhost", "10.", "192.168.")):
                if "{{" not in url:
                    findings.append(
                        SecurityFinding("ssrf_risk", "error", "Internal/private URL in HTTP node", node_id=n.id)
                    )

        body = str(data.get("body") or data.get("message") or "")
        if len(body) > 50000:
            findings.append(
                SecurityFinding("large_payload", "warning", "Very large template may cause abuse", node_id=n.id)
            )

    errors = sum(1 for f in findings if f.severity == "error")
    return SecurityReport(ok=errors == 0, findings=findings)
