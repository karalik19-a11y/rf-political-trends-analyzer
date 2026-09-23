"""Daily collection scheduler using APScheduler."""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .collector import collect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def job_collect():
    logger.info("=== Scheduled collection started at %s ===", datetime.utcnow().isoformat())
    try:
        n = collect()
        logger.info("=== Collection finished, new items: %d ===", n)
    except Exception as e:
        logger.exception("Scheduled collection failed: %s", e)


def run_scheduler(hour: int = 6, minute: int = 0):
    """
    Run blocking scheduler that collects every day at the given UTC time.
    Default: 06:00 UTC.
    """
    scheduler = BlockingScheduler(timezone="UTC")
    trigger = CronTrigger(hour=hour, minute=minute)
    scheduler.add_job(job_collect, trigger, id="daily_collect", replace_existing=True)
    logger.info("Scheduler started. Daily collection at %02d:%02d UTC", hour, minute)
    logger.info("Press Ctrl+C to stop.")
    try:
        # Run once immediately on start
        job_collect()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RF Political Trends daily collector")
    parser.add_argument("--hour", type=int, default=6, help="UTC hour for daily run (0-23)")
    parser.add_argument("--minute", type=int, default=0, help="UTC minute (0-59)")
    args = parser.parse_args()
    run_scheduler(hour=args.hour, minute=args.minute)
