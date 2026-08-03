import argparse

from air_transport_statistics.pipeline.main import run
from air_transport_statistics.update_models.main import pipeline_models
from air_transport_statistics.create_visualizations.main import create_visualizations


def run_all() -> int:
    status = run()
    if status != 0:
        return status
    pipeline_models()
    create_visualizations()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="air-transport-statistics",
        description="Air transport statistics pipeline",
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="run-all",
        choices=[
            "pipeline",
            "update-models",
            "create-visualizations",
            "run-all",
        ],
        help="Process to run (default: %(default)s)",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "pipeline":
        return run()
    elif args.command == "update-models":
        pipeline_models()
        return 0
    elif args.command == "create-visualizations":
        create_visualizations()
        return 0
    else:
        return run_all()


if __name__ == "__main__":
    raise SystemExit(main())
