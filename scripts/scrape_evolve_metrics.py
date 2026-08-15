#!/usr/bin/env python3
"""Scrape the evolution metrics endpoint and emit Prometheus text format.

This is the "wire up monitoring" piece for the
``GET /api/v1/evolve/metrics`` endpoint. Drop-in for a
`node_exporter textfile collector <https://github.com/prometheus/node_exporter#textfile-collector>`_
or run on a cron to page on critical severity.

Examples
--------
Run once and print to stdout::

    python scripts/scrape_evolve_metrics.py -t <tenant-id> -g <graph-id> \\
        -k <api-key> -u http://localhost:8000

Write a Prometheus textfile for node_exporter and page on criticals::

    python scripts/scrape_evolve_metrics.py -t ... -g ... -k ... \\
        --out /var/lib/node_exporter/textfile_collector/evolve.prom \\
        --deadman /var/lib/node_exporter/textfile_collector/evolve_deadman.prom

Cron (every 5 minutes; exit 2 when critical alerts are active)::

    1-59/5 * * * * /home/ravi/Projects/FAIM/scripts/scrape_evolve_metrics.py \\
        -t <tenant-id> -g <graph-id> -k <api-key> \\
        --out /var/lib/node_exporter/textfile_collector/evolve.prom \\
        >> /var/log/evolve_scrape.log 2>&1 || \\
        curl -fsS -X POST <pagerduty-webhook> -d "$(cat /var/log/evolve_scrape.log)"

Exit codes
----------
0  scrape OK, no critical alerts
2  scrape OK, at least one critical alert (badge = backup_coverage_gap)
3  endpoint unreachable / auth failed / HTTP error
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode


def _fmt(labels: Dict[str, str], value: str, help_text: str, name: str) -> List[str]:
    label_part = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return [
        f"# HELP {name} {help_text}",
        f"# TYPE {name} gauge",
        f"{name}{{{label_part}}} {value}",
    ]


def metrics_to_text(
    data: Dict[str, Any], graph_id: str, scrape_ts: int = 0
) -> str:
    """Convert the evolve metrics payload to Prometheus text exposition.

    Returns a single string of plain ``# HELP``/``# TYPE``/sample lines.
    """
    lines: List[str] = []
    light = {"graph_id": graph_id}

    cycles = data.get("cycles") or {}
    light = {"graph_id": graph_id}
    lines += _fmt(light, str(int(cycles.get("count", 0) or 0)),
                  "Completed evolution cycles", "faim_evolve_cycles_completed")
    lines += _fmt(light, str(int(cycles.get("last_version", 0) or 0)),
                  "Version of the latest completed evolution cycle",
                  "faim_evolve_last_version")
    lines += _fmt(light, str(int(cycles.get("last_merges", 0) or 0)),
                  "Merges performed by the latest cycle", "faim_evolve_last_merges")
    lines += _fmt(light, str(int(cycles.get("last_prunes", 0) or 0)),
                  "Nodes pruned by the latest cycle", "faim_evolve_last_prunes")
    lines += _fmt(light, str(int(cycles.get("last_inventions", 0) or 0)),
                  "Inventions by the latest cycle", "faim_evolve_last_inventions")

    safety = data.get("data_safety") or {}
    lines += _fmt(light, str(int(safety.get("backups_available", 0) or 0)),
                  "Pre-action backups currently stored",
                  "faim_evolve_backups_available")
    lines += _fmt(light, str(int(safety.get("latest_cycle_backups", 0) or 0)),
                  "Pre-action backups recorded for the latest cycle",
                  "faim_evolve_backups_latest_cycle")
    lines += _fmt(light, "1" if safety.get("coverage_ok") else "0",
                  "1 when every pruned node of the latest cycle has a backup",
                  "faim_evolve_backup_coverage_ok")

    learning = data.get("learning") or {}
    lines += _fmt(light, "1" if learning.get("enabled") else "0",
                  "Evolution learning flag enabled", "faim_evolve_learning_enabled")
    lines += _fmt(light, "1" if learning.get("learned") else "0",
                  "Evolution policy has learned (moved from defaults)",
                  "faim_evolve_learning_learned")
    lines += _fmt(light, "1" if learning.get("trust_ready") else "0",
                  "1 when learning has enough feedback to be trusted",
                  "faim_evolve_learning_trust_ready")
    lines += _fmt(light, str(int(learning.get("outcomes_count", 0) or 0)),
                  "Evolution feedback outcome rows", "faim_evolve_learning_outcomes")
    lines += _fmt(light, str(int(learning.get("knob_drift_count", 0) or 0)),
                  "Policy knobs moved from defaults", "faim_evolve_learning_knob_drift")
    slope = learning.get("reward_trend_slope")
    lines += _fmt(light, "nan" if slope is None else f"{slope}",
                  "Linear slope of reward vs graph version",
                  "faim_evolve_learning_reward_trend")

    alerts = data.get("alerts") or []
    if alerts:
        lines.append("# HELP faim_evolve_alert Active evolution health alerts (1 present)")
        lines.append("# TYPE faim_evolve_alert gauge")
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        label_part = ",".join(
            f'{k}="{alert.get(k, "")}"'
            for k in ("code", "level")
        )
        lines.append(f'faim_evolve_alert{{{label_part}}} 1')

    lines += [
        "# HELP faim_evolve_scrape_ok 1 if this scrape produced fresh metrics",
        "# TYPE faim_evolve_scrape_ok gauge",
        f'faim_evolve_scrape_ok{{graph_id="{graph_id}"}} 1',
        "# HELP faim_evolve_updated_timestamp_seconds Unix time of the last "
        "successful metrics scrape (staleness source)",
        "# TYPE faim_evolve_updated_timestamp_seconds gauge",
        f'faim_evolve_updated_timestamp_seconds{{graph_id="{graph_id}"}} '
        f"{int(scrape_ts)}",
    ]
    lines.append("")
    return "\n".join(lines)


def _write_deadman(
    path: Optional[str],
    graph_id: str,
    *,
    ok: int,
    scrape_ts: int = 0,
    current_ts: int = 0,
) -> None:
    """Write the deadman marker file.

    The marker carries the last successful scrape timestamp so a Prometheus
    rule can alert on ``faim_evolve_scrape_ok == 0`` or on a stale
    ``faim_evolve_updated_timestamp_seconds`` (staleness = the last successful
    scrape is too old).
    """
    if not path:
        return
    age_seconds = max(0, int(current_ts or time.time()) - int(scrape_ts))
    lines = [
        "# HELP faim_evolve_scrape_ok 1 if the most recent scrape succeeded",
        "# TYPE faim_evolve_scrape_ok gauge",
        f'faim_evolve_scrape_ok{{graph_id="{graph_id}"}} {ok}',
        "# HELP faim_evolve_updated_timestamp_seconds Unix time of the last "
        "successful metrics scrape",
        "# TYPE faim_evolve_updated_timestamp_seconds gauge",
        f'faim_evolve_updated_timestamp_seconds{{graph_id="{graph_id}"}} '
        f"{int(scrape_ts)}",
        "# HELP faim_evolve_scrape_failure_age_seconds Seconds since the last "
        "successful metrics scrape",
        "# TYPE faim_evolve_scrape_failure_age_seconds gauge",
        f'faim_evolve_scrape_failure_age_seconds{{graph_id="{graph_id}"}} '
        f"{age_seconds}",
        "",
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _fetch(path: str, base_url: str, api_key: str, tenant_id: str) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    req = urllib.request.Request(url, headers={"X-Tenant-Id": tenant_id,
                                               "X-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - operator supplied URL
        return json.loads(resp.read().decode("utf-8"))


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-u", "--base-url", default="http://localhost:8000")
    parser.add_argument("-t", "--tenant-id", required=True)
    parser.add_argument("-g", "--graph-id", required=True)
    parser.add_argument("-k", "--api-key", required=True)
    parser.add_argument("--out", default=None,
                        help="write Prometheus text to this textfile path")
    parser.add_argument("--deadman", default=None,
                        help="optional textfile path for scrape-failure markers")
    args = parser.parse_args(argv)

    scrape_ts = int(time.time())
    try:
        data = _fetch(
            f"/api/v1/evolve/metrics?{urlencode({'graph_id': args.graph_id})}",
            args.base_url,
            args.api_key,
            args.tenant_id,
        )
    except urllib.error.HTTPError as exc:
        _write_deadman(args.deadman, args.graph_id, ok=0)
        print(f"evolve metrics HTTP error {exc.code}: {exc.reason}", file=sys.stderr)
        return 3
    except urllib.error.URLError as exc:
        _write_deadman(args.deadman, args.graph_id, ok=0)
        print(f"evolve metrics unreachable: {exc.reason}", file=sys.stderr)
        return 3
    except Exception as exc:  # nosec B110
        _write_deadman(args.deadman, args.graph_id, ok=0)
        print(f"evolve metrics scrape failed: {exc!r}", file=sys.stderr)
        return 3

    text = metrics_to_text(data, args.graph_id, scrape_ts)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text, end="")
    _write_deadman(args.deadman, args.graph_id, ok=1, scrape_ts=scrape_ts)

    criticals = [
        alert for alert in data.get("alerts") or []
        if alert.get("level") == "critical"
    ]
    print(f"scrape_ok graph={args.graph_id} criticals={len(criticals)}", file=sys.stderr)
    return 2 if criticals else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))