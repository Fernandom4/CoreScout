import argparse
from datetime import date, timedelta
import os
import dlt

from sources.corescout import corescout_source


def run_pipeline(start_date: date, end_date: date = None, dry_run: bool = False) -> None:
    """Run the CoreScout ingestion pipeline.

    Loads reference data and orders from the CoreScout API into DuckDB.

    Args:
        start_date: first date to load orders for
        end_date:   last date to load orders for. Defaults to yesterday.
        dry_run:    if True, print what would be loaded without actually loading
    """
    if end_date is None:
        end_date = date.today() - timedelta(days=1)

    if dry_run:
        print(f"Dry run: would load orders from {start_date} to {end_date}")
        days = (end_date - start_date).days + 1
        print(f"Total days: {days}")
        return

    print(f"Loading orders from {start_date} to {end_date}")

    pipeline = dlt.pipeline(
        pipeline_name="corescout",
        destination=dlt.destinations.duckdb(
            credentials=os.environ.get("DUCKDB_PATH", "/data/corescout.duckdb")
        ),
        dataset_name="raw",
    )

    current = start_date
    while current <= end_date:
        source = corescout_source(
            start_date=current,
            end_date=current,
            as_of_date=current,
        )
        load_info = pipeline.run(source)
        print(f"{current}: {load_info}")
        current += timedelta(days=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoreScout ingestion pipeline")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        required=True,
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=None,
        help="End date in YYYY-MM-DD format. Defaults to yesterday.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be loaded without actually loading",
    )

    args = parser.parse_args()
    run_pipeline(
        start_date=args.start_date,
        end_date=args.end_date,
        dry_run=args.dry_run,
    )
