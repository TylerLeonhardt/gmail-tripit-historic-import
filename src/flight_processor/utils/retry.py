"""Retry utilities with exponential backoff"""
import time
import random
import logging
import backoff
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


@backoff.on_exception(
    backoff.expo,
    (HttpError, ConnectionError),
    max_tries=5,
    max_time=300,
    jitter=backoff.full_jitter
)
def gmail_api_call_with_backoff(operation):
    """Execute Gmail API call with exponential backoff retry logic"""
    return operation()


def make_request_with_backoff(request_func, max_retries=5):
    """
    Manual retry implementation with exponential backoff
    
    Args:
        request_func: Function to execute
        max_retries: Maximum number of retry attempts
    
    Returns:
        Result of request_func()
    """
    for n in range(max_retries):
        try:
            return request_func()
        except HttpError as error:
            if error.resp.status in [403, 429, 500, 503]:
                if n == max_retries - 1:
                    raise
                wait_time = (2 ** n) + random.random()
                logger.warning(f"Rate limit hit, retrying in {wait_time:.2f}s (attempt {n+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise
