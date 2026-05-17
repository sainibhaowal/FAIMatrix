"""Operational admin alerts and email delivery helpers."""

from __future__ import annotations

import html
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Sequence

import httpx

logger = logging.getLogger(__name__)

DEFAULT_ALERT_FROM = "FAIMATRIX <noreply@faimatrix.com>"
ALERT_STALE_BACKUP_HOURS = 24


@dataclass(frozen=True)
class AdminAlert:
    id: str
    severity: str
    title: str
    message: str
    source: str
    created_at: str
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
        }


def _parse_email_list(*raw_values: str | None) -> list[str]:
    recipients: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        if not raw:
            continue
        candidates: list[str] = []
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            candidates.extend(str(value) for value in parsed)
        elif isinstance(parsed, dict):
            candidates.extend(str(value) for value in parsed.values())
        elif isinstance(parsed, str):
            candidates.append(parsed)
        else:
            candidates.extend(raw.split(","))

        for candidate in candidates:
            email = candidate.strip().lower()
            if email and email not in seen:
                seen.add(email)
                recipients.append(email)
    return recipients


def get_admin_recipients() -> list[str]:
    recipients = _parse_email_list(
        os.getenv("FAIM_ALERT_EMAILS_JSON"),
        os.getenv("FAIM_ADMIN_EMAILS_JSON"),
        os.getenv("FAIM_ADMIN_EMAIL"),
    )
    return recipients


def get_alert_from() -> str:
    return os.getenv("FAIM_ALERT_FROM_EMAIL", DEFAULT_ALERT_FROM)


def build_delivery_snapshot() -> Dict[str, Any]:
    recipients = get_admin_recipients()
    return {
        "provider": "resend",
        "enabled": bool(os.getenv("RESEND_API_KEY")),
        "from_email": get_alert_from(),
        "recipients": recipients,
        "recipients_count": len(recipients),
    }


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _alert(
    severity: str,
    title: str,
    message: str,
    source: str,
    *,
    suffix: str,
) -> AdminAlert:
    return AdminAlert(
        id=f"{source}:{suffix}",
        severity=severity,
        title=title,
        message=message,
        source=source,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def build_operational_alerts(
    *,
    health: Dict[str, Any],
    readiness: Dict[str, Any],
    runtime: Dict[str, Any],
    backups: Sequence[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """Derive operational alerts from the current runtime snapshot."""

    alerts: list[AdminAlert] = []

    health_status = str(health.get("status") or "unknown").lower()
    if health_status not in {"ok", "healthy"}:
        alerts.append(
            _alert(
                "critical",
                "Service health degraded",
                f"Health endpoint returned {health_status!r}. Investigate the API and proxy layer.",
                "health",
                suffix=health_status or "unknown",
            )
        )

    readiness_status = str(readiness.get("status") or "unknown").lower()
    if readiness_status != "ready":
        missing_tables = readiness.get("missing_tables") or []
        missing_fragment = (
            f" Missing tables: {', '.join(missing_tables)}." if missing_tables else ""
        )
        alerts.append(
            _alert(
                "critical",
                "Readiness check failed",
                "Database or migration readiness is not green." + missing_fragment,
                "readiness",
                suffix=readiness_status or "unknown",
            )
        )

    if not runtime.get("admin_key_configured", False):
        alerts.append(
            _alert(
                "warning",
                "Admin key not configured",
                "FAIM_ADMIN_KEY is missing. Admin controls will not be reachable.",
                "runtime",
                suffix="admin-key",
            )
        )

    if not runtime.get("auth_db_primary", False):
        alerts.append(
            _alert(
                "warning",
                "Auth DB fallback enabled",
                "Primary database-backed authentication is not active.",
                "runtime",
                suffix="auth-db-fallback",
            )
        )

    if not runtime.get("auth_scope_enforcement_enabled", False):
        alerts.append(
            _alert(
                "warning",
                "Auth scope enforcement disabled",
                "Tenant isolation checks are not fully enforced.",
                "runtime",
                suffix="auth-scope",
            )
        )

    if not backups:
        alerts.append(
            _alert(
                "warning",
                "No backups found",
                "The configured backup directory is empty. Run a backup immediately.",
                "backups",
                suffix="empty",
            )
        )
    else:
        latest = backups[0]
        latest_at = _parse_iso_timestamp(str(latest.get("modified_at") or ""))
        if latest_at is not None:
            age_hours = (
                datetime.now(timezone.utc) - latest_at
            ).total_seconds() / 3600.0
            if age_hours >= ALERT_STALE_BACKUP_HOURS:
                alerts.append(
                    _alert(
                        "warning",
                        "Backups are stale",
                        f"Latest backup is {age_hours:.1f} hours old. Run a new backup.",
                        "backups",
                        suffix="stale",
                    )
                )

    alerts.sort(key=lambda item: item.created_at, reverse=True)
    return [item.to_dict() for item in alerts]


def summarize_alerts(alerts: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    summary = {"critical": 0, "warning": 0, "info": 0, "success": 0}
    for alert in alerts:
        severity = str(alert.get("severity") or "info").lower()
        if severity in summary:
            summary[severity] += 1
    summary["total"] = len(alerts)
    return summary


def _render_alert_rows(alerts: Sequence[Dict[str, Any]]) -> str:
    if not alerts:
        return (
            "<tr><td style='padding:14px 16px;color:#64748b;'>"
            "No active alerts right now."
            "</td></tr>"
        )

    rows: list[str] = []
    for alert in alerts:
        severity = html.escape(str(alert.get("severity") or "info").upper())
        title = html.escape(str(alert.get("title") or "Alert"))
        message = html.escape(str(alert.get("message") or ""))
        created_at = html.escape(str(alert.get("created_at") or ""))
        source = html.escape(str(alert.get("source") or ""))
        rows.append(f"""
            <tr>
              <td style="padding:14px 16px;border-bottom:1px solid #1f2937;">
                <div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#94a3b8;margin-bottom:6px;">
                  {severity} · {source}
                </div>
                <div style="font-size:16px;font-weight:700;color:#f8fafc;margin-bottom:4px;">
                  {title}
                </div>
                <div style="font-size:13px;line-height:1.55;color:#cbd5e1;">
                  {message}
                </div>
                <div style="font-size:11px;color:#64748b;margin-top:8px;">
                  {created_at}
                </div>
              </td>
            </tr>
            """)
    return "".join(rows)


def render_alert_email(
    *,
    alerts: Sequence[Dict[str, Any]],
    delivery: Dict[str, Any],
    test_mode: bool = False,
) -> Dict[str, str]:
    summary = summarize_alerts(alerts)
    subject = (
        "[FAIM] Admin alerts test"
        if test_mode
        else f"[FAIM] {summary['critical']} critical, {summary['warning']} warning alerts"
    )
    headline = (
        "Admin alert delivery test" if test_mode else "Operational alerts from FAIM"
    )
    intro = (
        "This is a test message confirming alert delivery."
        if test_mode
        else "The current control-plane snapshot has generated the following alerts."
    )
    rows = _render_alert_rows(alerts)
    recipients = ", ".join(
        html.escape(email) for email in delivery.get("recipients", [])
    )

    html_body = f"""
    <div style="background:#020617;color:#e2e8f0;font-family:Inter,system-ui,sans-serif;padding:32px 0;">
      <div style="max-width:720px;margin:0 auto;padding:0 20px;">
        <div style="border:1px solid #1f2937;border-radius:20px;background:#0f172a;padding:28px;">
          <div style="font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#38bdf8;margin-bottom:12px;">
            FAIM admin alerts
          </div>
          <h1 style="margin:0 0 10px;font-size:28px;line-height:1.2;color:#f8fafc;">
            {html.escape(headline)}
          </h1>
          <p style="margin:0 0 20px;font-size:14px;line-height:1.65;color:#cbd5e1;">
            {html.escape(intro)}
          </p>
          <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;">
            <span style="padding:8px 12px;border-radius:999px;background:#111827;border:1px solid #334155;font-size:12px;">
              Recipients: {recipients or "none"}
            </span>
            <span style="padding:8px 12px;border-radius:999px;background:#111827;border:1px solid #334155;font-size:12px;">
              Critical: {summary["critical"]}
            </span>
            <span style="padding:8px 12px;border-radius:999px;background:#111827;border:1px solid #334155;font-size:12px;">
              Warning: {summary["warning"]}
            </span>
          </div>
          <table style="width:100%;border-collapse:collapse;border:1px solid #1f2937;border-radius:16px;overflow:hidden;">
            {rows}
          </table>
        </div>
      </div>
    </div>
    """

    text_lines = [
        headline,
        intro,
        f"Recipients: {', '.join(delivery.get('recipients', [])) or 'none'}",
        f"Critical: {summary['critical']} Warning: {summary['warning']} Total: {summary['total']}",
    ]
    for alert in alerts:
        text_lines.append(
            f"- [{alert.get('severity', 'info')}] {alert.get('title', 'Alert')}: {alert.get('message', '')}"
        )

    return {
        "subject": subject,
        "html": html_body,
        "text": "\n".join(text_lines),
    }


def send_admin_alert_email(
    *,
    alerts: Sequence[Dict[str, Any]],
    delivery: Dict[str, Any],
    test_mode: bool = False,
) -> Dict[str, Any]:
    recipients = list(delivery.get("recipients") or [])
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return {
            "status": "disabled",
            "message": "RESEND_API_KEY is not configured.",
            "provider": delivery.get("provider", "resend"),
            "recipients": recipients,
            "sent": False,
        }

    if not recipients:
        return {
            "status": "disabled",
            "message": "No admin alert recipients are configured.",
            "provider": delivery.get("provider", "resend"),
            "recipients": recipients,
            "sent": False,
        }

    payload = render_alert_email(alerts=alerts, delivery=delivery, test_mode=test_mode)
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": delivery.get("from_email") or DEFAULT_ALERT_FROM,
                "to": recipients,
                "subject": payload["subject"],
                "html": payload["html"],
                "text": payload["text"],
            },
            timeout=15.0,
        )
    except Exception as exc:  # pragma: no cover - network/runtime failure
        logger.exception("Failed to send admin alert email: %s", exc)
        return {
            "status": "error",
            "message": f"Failed to send email: {exc}",
            "provider": delivery.get("provider", "resend"),
            "recipients": recipients,
            "sent": False,
        }

    if response.status_code not in {200, 201}:
        return {
            "status": "error",
            "message": f"Resend returned HTTP {response.status_code}",
            "provider": delivery.get("provider", "resend"),
            "recipients": recipients,
            "sent": False,
            "response": response.text[:500],
        }

    return {
        "status": "sent",
        "message": "Admin alert email sent.",
        "provider": delivery.get("provider", "resend"),
        "recipients": recipients,
        "sent": True,
    }
