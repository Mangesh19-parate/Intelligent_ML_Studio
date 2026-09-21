"""
Durable Task Worker Daemon (Dedicated Background Worker Process).
"""

import os
import sys
import time
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.tasks.worker import poll_and_execute_task

logger = logging.getLogger("ml_studio.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def run_worker_loop(poll_interval: float = 2.0):
    logger.info("Starting Intelligent ML Studio Dedicated Worker daemon...")
    while True:
        try:
            with SessionLocal() as db:
                processed = poll_and_execute_task(db)
                if not processed:
                    time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user. Terminating gracefully...")
            break
        except Exception as e:
            logger.exception(f"Worker encountered error in polling loop: {e}")
            time.sleep(poll_interval)


if __name__ == "__main__":
    run_worker_loop()
