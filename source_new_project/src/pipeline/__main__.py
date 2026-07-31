from __future__ import annotations

import argparse
import sys

from .orchestrator import run_from_project_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run")
    run.add_argument("--month")
    run.add_argument("--project-root", default=None)
    backfill = commands.add_parser("backfill")
    backfill.add_argument("--start", required=True)
    backfill.add_argument("--end", required=True)
    backfill.add_argument("--project-root", default=None)
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["run"])
    try:
        if args.command == "run":
            run_from_project_root(args.project_root or ".", "run", month=args.month)
        else:
            run_from_project_root(args.project_root or ".", "backfill", start=args.start, end=args.end)
    except Exception as exc:
        print(f"pipeline failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
