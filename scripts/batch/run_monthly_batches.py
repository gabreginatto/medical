#!/usr/bin/env python3
"""
Monthly Batch Runner for PNCP Medical Data Processing
Automates running main.py month-by-month to avoid overwhelming the system.
"""

import subprocess
import sys
import os
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monthly_batch_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MonthlyBatchRunner:
    """Runs main.py month-by-month for a specified number of months"""

    def __init__(self, state: str, start_year: int, start_month: int, num_months: int):
        self.state = state
        self.start_year = start_year
        self.start_month = start_month
        self.num_months = num_months
        self.progress_file = f'logs/batch_progress_{state}_{start_year}{start_month:02d}.json'
        self.completed_months = self.load_progress()

    def load_progress(self):
        """Load progress from previous runs if any"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"📂 Loaded progress: {len(data['completed'])} months already completed")
                    return set(data['completed'])
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        return set()

    def save_progress(self, month_key: str):
        """Save progress after each successful month"""
        self.completed_months.add(month_key)

        os.makedirs('logs', exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump({
                'state': self.state,
                'start_year': self.start_year,
                'start_month': self.start_month,
                'total_months': self.num_months,
                'completed': list(self.completed_months),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)

        logger.info(f"💾 Progress saved: {len(self.completed_months)}/{self.num_months} months completed")

    def get_month_range(self, year: int, month: int):
        """Get start and end dates for a given month"""
        start_date = datetime(year, month, 1)

        # Get last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        # Format as YYYYMMDD
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        return start_str, end_str, start_date.strftime('%B %Y')

    def run_month(self, year: int, month: int):
        """Run main.py for a specific month"""
        start_date, end_date, month_name = self.get_month_range(year, month)
        month_key = f"{year}-{month:02d}"

        # Check if already completed
        if month_key in self.completed_months:
            logger.info(f"⏭️  Skipping {month_name} (already completed)")
            return True

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🚀 Starting processing for: {month_name}")
        logger.info(f"   State: {self.state}")
        logger.info(f"   Date Range: {start_date} to {end_date}")
        logger.info("=" * 80)

        # Build command
        cmd = [
            'python3',
            'main.py',
            '--start-date', start_date,
            '--end-date', end_date,
            '--states', self.state
        ]

        logger.info(f"📝 Running: {' '.join(cmd)}")

        try:
            # Run main.py and wait for completion
            # Set cwd to project root (2 levels up from scripts/batch/)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            result = subprocess.run(
                cmd,
                cwd=project_root,
                check=True,
                capture_output=False,  # Let output flow to console
                text=True
            )

            logger.info(f"✅ Completed {month_name} successfully")
            self.save_progress(month_key)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to process {month_name}: {e}")
            logger.error(f"   You can resume later - progress has been saved")
            return False

        except KeyboardInterrupt:
            logger.warning(f"\n⚠️  Interrupted during {month_name}")
            logger.info(f"   You can resume later - progress has been saved")
            raise

    def run_all(self):
        """Run all months in sequence"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🤖 MONTHLY BATCH RUNNER - PNCP Medical Data Processing")
        logger.info("=" * 80)
        logger.info(f"State: {self.state}")
        logger.info(f"Starting: {self.start_year}-{self.start_month:02d}")
        logger.info(f"Total Months: {self.num_months}")
        logger.info(f"Already Completed: {len(self.completed_months)}")
        logger.info("=" * 80)

        start_time = datetime.now()
        current_date = datetime(self.start_year, self.start_month, 1)

        success_count = len(self.completed_months)
        failed_months = []

        for i in range(self.num_months):
            year = current_date.year
            month = current_date.month

            logger.info(f"\n📅 Processing month {i+1}/{self.num_months}")

            if self.run_month(year, month):
                if f"{year}-{month:02d}" not in self.completed_months:
                    success_count += 1
            else:
                failed_months.append(current_date.strftime('%B %Y'))
                logger.warning(f"⚠️  Stopping batch run due to error")
                break

            # Move to next month
            current_date += relativedelta(months=1)

        # Final summary
        total_time = datetime.now() - start_time
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 BATCH RUN SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Months Requested: {self.num_months}")
        logger.info(f"Successfully Completed: {success_count}")
        logger.info(f"Failed: {len(failed_months)}")
        if failed_months:
            logger.info(f"Failed Months: {', '.join(failed_months)}")
        logger.info(f"Total Time: {total_time}")
        logger.info("=" * 80)

        if success_count == self.num_months:
            logger.info("🎉 All months completed successfully!")
        else:
            logger.warning("⚠️  Some months failed. You can re-run this script to resume.")


def main():
    parser = argparse.ArgumentParser(
        description='Run PNCP medical data processing month-by-month',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process 6 months starting from January 2024 for São Paulo
  python run_monthly_batches.py --state SP --start 2024-01 --months 6

  # Process entire year 2023 for Rio de Janeiro
  python run_monthly_batches.py --state RJ --start 2023-01 --months 12

  # Resume a previous run (uses same parameters, skips completed months)
  python run_monthly_batches.py --state SP --start 2024-01 --months 6
        """
    )

    parser.add_argument('--state', required=True,
                       help='State code (e.g., SP, RJ, MG)')
    parser.add_argument('--start', required=True,
                       help='Start month in YYYY-MM format (e.g., 2024-01)')
    parser.add_argument('--months', type=int, required=True,
                       help='Number of months to process')

    args = parser.parse_args()

    # Parse start date
    try:
        start_parts = args.start.split('-')
        start_year = int(start_parts[0])
        start_month = int(start_parts[1])

        if not (1 <= start_month <= 12):
            logger.error("❌ Month must be between 01 and 12")
            return

    except (ValueError, IndexError):
        logger.error("❌ Invalid start date format. Use YYYY-MM (e.g., 2024-01)")
        return

    # Validate months
    if args.months < 1:
        logger.error("❌ Number of months must be at least 1")
        return

    # Create and run batch processor
    try:
        runner = MonthlyBatchRunner(
            state=args.state.upper(),
            start_year=start_year,
            start_month=start_month,
            num_months=args.months
        )
        runner.run_all()

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Batch run interrupted by user")
        logger.info("💡 You can resume by running the same command again")
        sys.exit(1)


if __name__ == "__main__":
    main()
