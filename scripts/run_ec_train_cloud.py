"""Preflight and run EC Train with cloud-friendly defaults."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ec_train.bidtabs import PAY_ITEM_TARGET, scan_bidtabs
from ec_train.cli import run as ec_train_run
from ec_train.config import Config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight and run EC Train.")
    parser.add_argument("--count", type=int, default=3, help="Number of contracts to process.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Download/output directory.",
    )
    parser.add_argument(
        "--bidtabs-path",
        type=Path,
        default=None,
        help="Path to BidTabs export (CSV/Excel).",
    )
    parser.add_argument(
        "--resume-file",
        type=Path,
        default=None,
        help="Resume from a prior session log.",
    )
    parser.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        default=True,
        help="Enable headless mode for scraping.",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Disable headless mode for scraping.",
    )
    parser.add_argument(
        "--force-new-session",
        action="store_true",
        default=False,
        help="Ignore previous sessions.",
    )
    parser.add_argument(
        "--min-job-size",
        type=float,
        default=None,
        help="Minimum contract amount (inclusive).",
    )
    parser.add_argument(
        "--max-job-size",
        type=float,
        default=None,
        help="Maximum contract amount (inclusive).",
    )
    parser.add_argument(
        "--extract",
        dest="extract",
        action="store_true",
        default=True,
        help="Enable content extraction.",
    )
    parser.add_argument(
        "--no-extract",
        dest="extract",
        action="store_false",
        help="Disable content extraction.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = Config.from_env()
    output_dir = args.output_dir or cfg.download_dir
    bidtabs_path = args.bidtabs_path or cfg.bidtabs_path
    if not bidtabs_path:
        raise SystemExit(
            "BidTabs path must be provided via --bidtabs-path or EC_TRAIN_BIDTABS_PATH."
        )
    bidtabs_path = Path(bidtabs_path)
    if not bidtabs_path.exists():
        raise SystemExit(f"BidTabs path does not exist: {bidtabs_path}")

    try:
        contracts = scan_bidtabs(bidtabs_path)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Unable to read BidTabs file: {exc}") from exc

    if not contracts:
        print(f"No contracts found for pay item {PAY_ITEM_TARGET}.")
        return

    ec_train_run(
        count=args.count,
        output_dir=output_dir,
        resume_file=args.resume_file,
        headless=args.headless,
        force_new_session=args.force_new_session,
        min_job_size=args.min_job_size,
        max_job_size=args.max_job_size,
        bidtabs_path=bidtabs_path,
        extract=args.extract,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)
