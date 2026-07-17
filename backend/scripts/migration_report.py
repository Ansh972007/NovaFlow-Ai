#!/usr/bin/env python3
"""Generate pre/post migration health reports for the data platform."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure backend root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine
from app.data.migration_health import migration_impact_report, post_migration_verify, write_report
from app.data.partitioning import ensure_monthly_partitions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("pre", "post", "partitions"), default="pre")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    if args.phase == "pre":
        report = migration_impact_report(engine)
    elif args.phase == "partitions":
        report = ensure_monthly_partitions(engine)
    else:
        report = post_migration_verify(engine)

    text = json.dumps(report, indent=2, default=str)
    print(text)
    if args.out:
        write_report(args.out, report)
    return 0 if report.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
