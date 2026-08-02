import argparse

from air_transport_statistics.pipeline.main import run
from air_transport_statistics.update_models.main import pipeline_models


def run_all() -> None:
    run()
    pipeline_models()


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
            "run-all",
        ],
        help="Process to run (default: %(default)s)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "pipeline":
        run()
    elif args.command == "update-models":
        pipeline_models()
    else:
        run_all()


if __name__ == "__main__":
    main()