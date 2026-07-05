import asyncio
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy.orm import Session

from app.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from app.database import EvalRegressionAlert, EvalRun, EvalSuite
from app.services.webhooks import post_alert_notification, post_opsgenie_alert, post_pagerduty_alert

logger = logging.getLogger("novaflow.alerts")


def alert_dict(row: EvalRegressionAlert) -> dict:
    return {
        "id": row.id,
        "suite_id": row.suite_id,
        "min_pass_rate": row.min_pass_rate,
        "drop_points": row.drop_points,
        "webhook_url": row.webhook_url or "",
        "pagerduty_routing_key": row.pagerduty_routing_key or "",
        "opsgenie_api_key": ("••••" + row.opsgenie_api_key[-4:]) if row.opsgenie_api_key else "",
        "email_to": row.email_to or "",
        "cooldown_hours": row.cooldown_hours or 6,
        "enabled": bool(row.enabled),
        "last_alert_at": row.last_alert_at.isoformat() if row.last_alert_at else None,
        "create_time": row.create_time.isoformat() if row.create_time else None,
    }


def _pass_rate(run: EvalRun) -> float:
    if not run.total_count:
        return 0.0
    return round((run.pass_count / run.total_count) * 100, 1)


def _previous_run(db: Session, suite_id: int, exclude_id: int) -> EvalRun | None:
    return (
        db.query(EvalRun)
        .filter(EvalRun.suite_id == suite_id, EvalRun.id != exclude_id)
        .order_by(EvalRun.create_time.desc())
        .first()
    )


def _send_email_sync(to_addr: str, subject: str, body: str) -> bool:
    if not SMTP_HOST or not to_addr:
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or SMTP_USER or "novaflow@localhost"
    msg["To"] = to_addr
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], [to_addr], msg.as_string())
        return True
    except Exception as exc:
        logger.warning("Email alert failed: %s", exc)
        return False


async def send_email_alert(to_addr: str, subject: str, body: str) -> bool:
    return await asyncio.to_thread(_send_email_sync, to_addr, subject, body)


async def check_regression_alerts(db: Session, suite: EvalSuite, run: EvalRun) -> list[dict[str, Any]]:
    alerts = (
        db.query(EvalRegressionAlert)
        .filter(EvalRegressionAlert.suite_id == suite.id, EvalRegressionAlert.enabled == 1)
        .all()
    )
    if not alerts:
        return []

    current_rate = _pass_rate(run)
    prev = _previous_run(db, suite.id, run.id)
    prev_rate = _pass_rate(prev) if prev else None
    fired: list[dict[str, Any]] = []
    now = datetime.utcnow()

    for alert in alerts:
        if alert.last_alert_at:
            cooldown = timedelta(hours=max(1, alert.cooldown_hours or 6))
            if now - alert.last_alert_at < cooldown:
                continue

        reasons = []
        if current_rate < (alert.min_pass_rate or 80):
            reasons.append(f"pass rate {current_rate}% below minimum {alert.min_pass_rate}%")
        if prev_rate is not None and current_rate < prev_rate - (alert.drop_points or 10):
            reasons.append(f"dropped {prev_rate - current_rate:.1f} pts from previous {prev_rate}%")

        if not reasons:
            continue

        message = (
            f"Regression alert: benchmark suite \"{suite.name}\" (id {suite.id})\n"
            f"Run #{run.id}: {run.pass_count}/{run.total_count} passed ({current_rate}%)\n"
            + "\n".join(f"• {r}" for r in reasons)
        )
        payload = {
            "suite_id": suite.id,
            "suite_name": suite.name,
            "run_id": run.id,
            "pass_rate": current_rate,
            "previous_pass_rate": prev_rate,
            "reasons": reasons,
        }

        if alert.webhook_url:
            await post_alert_notification(alert.webhook_url, message, payload, event="eval.regression")
        if alert.pagerduty_routing_key:
            await post_pagerduty_alert(
                alert.pagerduty_routing_key,
                f"NovaFlow eval regression: {suite.name}",
                payload,
            )
        if alert.opsgenie_api_key:
            await post_opsgenie_alert(
                alert.opsgenie_api_key,
                f"Eval regression: {suite.name}",
                message,
                payload,
            )
        if alert.email_to:
            await send_email_alert(
                alert.email_to,
                f"[NovaFlow] Eval regression: {suite.name}",
                message,
            )

        alert.last_alert_at = now
        alert.update_time = now
        db.commit()
        fired.append({"alert_id": alert.id, "reasons": reasons})

    return fired


def suite_trends(db: Session, suite_id: int, workspace_id: int, limit: int = 30) -> list[dict]:
    runs = (
        db.query(EvalRun)
        .filter(EvalRun.suite_id == suite_id, EvalRun.workspace_id == workspace_id)
        .order_by(EvalRun.create_time.desc())
        .limit(limit)
        .all()
    )
    points = []
    for run in reversed(runs):
        points.append(
            {
                "run_id": run.id,
                "date": run.create_time.isoformat() if run.create_time else None,
                "pass_rate": _pass_rate(run),
                "pass_count": run.pass_count,
                "total_count": run.total_count,
                "avg_latency_ms": run.avg_latency_ms,
            }
        )
    return points


def comparison_trends(db: Session, workspace_id: int, suite_id: int | None = None, limit: int = 20) -> list[dict]:
    from app.database import EvalComparison

    q = db.query(EvalComparison).filter(EvalComparison.workspace_id == workspace_id)
    if suite_id:
        q = q.filter(EvalComparison.suite_id == suite_id)
    rows = q.order_by(EvalComparison.create_time.desc()).limit(limit).all()

    series = []
    for row in reversed(rows):
        try:
            payload = json.loads(row.results_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        assistants = payload.get("assistants", [])
        series.append(
            {
                "comparison_id": row.id,
                "suite_id": row.suite_id,
                "date": row.create_time.isoformat() if row.create_time else None,
                "assistants": [
                    {
                        "assistant_id": a.get("assistant_id"),
                        "assistant_name": a.get("assistant_name"),
                        "pass_rate": a.get("pass_rate"),
                    }
                    for a in assistants
                ],
            }
        )
    return series
