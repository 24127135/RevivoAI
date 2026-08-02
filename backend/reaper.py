import asyncio
import logging
import random

logger = logging.getLogger(__name__)


async def session_reaper_task(handler, interval_seconds: int = 300):
    """
    Background task that periodically invokes the SessionHandler's reaper
    to clean up expired sessions. Includes exponential backoff and jitter.
    """
    logger.info(f"Starting session reaper task with interval: {interval_seconds} seconds.")

    base_interval = interval_seconds
    max_backoff = 3600  # Cap backoff at 1 hour
    consecutive_errors = 0

    while True:
        try:
            # 1. Add a small jitter (0-5 seconds) to prevent multiple Uvicorn workers
            # from hitting the database at the exact same millisecond.
            jitter = random.uniform(0, 5)

            reaped_count = await handler.reap_expired_sessions()

            if reaped_count > 0:
                logger.info(f"Reaper successfully cleaned up {reaped_count} expired sessions.")

            # 2. Reset error counter on success
            consecutive_errors = 0

            # 3. Sleep is now INSIDE the try block to correctly catch CancelledError
            await asyncio.sleep(base_interval + jitter)

        except asyncio.CancelledError:
            # 4. Re-raise to maintain proper cancellation semantics for the event loop
            logger.info("Reaper task received cancellation signal. Shutting down cleanly.")
            raise

        except Exception as e:
            # 5. Exponential backoff logic for database/network failures
            consecutive_errors += 1
            backoff_multiplier = 2 ** (consecutive_errors - 1)
            sleep_time = min(base_interval * backoff_multiplier, max_backoff)

            logger.error(f"Reaper encountered an issue: {e}")
            logger.warning(f"Reaper backing off for {sleep_time} seconds before retrying.")

            # Still need to catch CancelledError during the backoff sleep
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                logger.info("Reaper task cancelled during error backoff. Shutting down.")
                raise