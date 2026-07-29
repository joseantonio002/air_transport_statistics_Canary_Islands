from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run")
    run.add_argument("--month")
    backfill = commands.add_parser("backfill")
    backfill.add_argument("--start", required=True)
    backfill.add_argument("--end", required=True)
    args = parser.parse_args()
    if args.command is None:
        parser.parse_args(["run"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
