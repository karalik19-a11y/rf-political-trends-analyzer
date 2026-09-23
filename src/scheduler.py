"""Daily collection scheduler using APScheduler."""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

try:
    from collector import collect
except ImportError:
    from .collector import collect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def job_collect():
    logger.info("=== Scheduled collection at %s ===", datetime.utcnow().isoformat())
    try:
        n = collect()
        logger.info("=== Done, new items: %d ===", n)
    except Exception as e:
        logger.exception("Scheduled collection failed: %s", e)


def run_scheduler(hour: int = 6, minute: int = 0):
    scheduler = BlockingScheduler(timezone="UTC")
    trigger = CronTrigger(hour=hour, minute=minute)
    scheduler.add_job(job_collect, trigger, id="daily_collect", replace_existing=True)
    logger.info("Scheduler started. Daily at %02d:%02d UTC", hour, minute)
    try:
        job_collect()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", type=int, default=6)
    parser.add_argument("--minute", type=int, default=0)
    args = parser.parse_args()
    run_scheduler(hour=args.hour, minute=args.minute)
