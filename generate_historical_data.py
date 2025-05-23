# generate_historical_data.py
import subprocess
import random
from datetime import date, timedelta
import argparse
import sys


def generate_past_business_days(n_days=300, include_some_saturdays=True, percent_saturdays=0.1):
    """
    Generate a list of business days (weekdays + occasional Saturdays) going back from today.

    Args:
        n_days: Number of business days to generate
        include_some_saturdays: Whether to include some Saturdays
        percent_saturdays: Percentage of Saturdays to include (0.0 to 1.0)

    Returns:
        List of dates in ISO format (YYYY-MM-DD)
    """
    days = []
    curr_date = date.today()
    count = 0

    while count < n_days:
        # Weekday (Mon-Fri = 0-4, Sat=5, Sun=6)
        if curr_date.weekday() < 5:  # Mon-Fri
            days.append(curr_date)
            count += 1
        elif curr_date.weekday() == 5 and include_some_saturdays:
            # Randomly include some Saturdays
            if random.random() < percent_saturdays:
                days.append(curr_date)
                count += 1

        # Move to previous day
        curr_date -= timedelta(days=1)

    # Reverse the list so oldest dates come first
    days.reverse()

    return [d.isoformat() for d in days]


def process_dates(dates, team, batch_size=1, periods=4, force_complete=False, dry_run=False):
    """
    Process a list of dates by calling the main.py script for each date or batch of dates.

    Args:
        dates: List of dates in ISO format (YYYY-MM-DD)
        team: Team name to use for scheduling
        batch_size: Number of days to process in each batch
        periods: Number of periods per day
        force_complete: Whether to force complete the schedule
        dry_run: If True, print commands but don't execute them
    """
    total_dates = len(dates)

    # Process dates in batches
    for i in range(0, total_dates, batch_size):
        batch = dates[i:i + batch_size]
        start_date = batch[0]
        days = len(batch)

        # Build command
        # Use the same Python interpreter that's running this script
        import sys
        cmd = [
            sys.executable, "main.py", "generate",
            "--team", team,
            "--start-date", start_date,
            "--days", str(days),
            "--periods", str(periods)
        ]

        if force_complete:
            cmd.append("--force-complete")

        # Print progress
        print(
            f"Processing batch {i // batch_size + 1}/{(total_dates + batch_size - 1) // batch_size}: {start_date} to {batch[-1]}")
        print(f"Command: {' '.join(cmd)}")

        # Execute command if not a dry run
        if not dry_run:
            try:
                result = subprocess.run(cmd, check=True)
                print(f"Batch completed with exit code: {result.returncode}")
            except subprocess.CalledProcessError as e:
                print(f"Error processing batch: {e}", file=sys.stderr)
                print("Continuing with next batch...")

        print("-" * 80)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate historical schedule data')
    parser.add_argument('--days', type=int, default=300, help='Number of business days to generate')
    parser.add_argument('--team', type=str, required=True, help='Team name')
    parser.add_argument('--batch-size', type=int, default=1, help='Number of days to process in each batch')
    parser.add_argument('--periods', type=int, default=4, help='Number of periods per day')
    parser.add_argument('--saturday-percent', type=float, default=0.1,
                        help='Percentage of Saturdays to include (0.0 to 1.0)')
    parser.add_argument('--force-complete', action='store_true', help='Force complete the schedule')
    parser.add_argument('--dry-run', action='store_true', help='Print commands but do not execute them')
    parser.add_argument('--start-idx', type=int, default=0, help='Start index in the date list (for resuming)')
    parser.add_argument('--end-idx', type=int, default=None, help='End index in the date list (for partial runs)')

    args = parser.parse_args()

    # Generate list of business days
    print(f"Generating {args.days} business days with {args.saturday_percent * 100:.1f}% Saturdays...")
    dates = generate_past_business_days(
        n_days=args.days,
        include_some_saturdays=args.saturday_percent > 0,
        percent_saturdays=args.saturday_percent
    )

    # Apply start and end indices
    if args.end_idx is not None:
        dates = dates[args.start_idx:args.end_idx]
    else:
        dates = dates[args.start_idx:]

    print(f"Processing {len(dates)} dates from {dates[0]} to {dates[-1]}")

    # Process the dates
    process_dates(
        dates=dates,
        team=args.team,
        batch_size=args.batch_size,
        periods=args.periods,
        force_complete=args.force_complete,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
