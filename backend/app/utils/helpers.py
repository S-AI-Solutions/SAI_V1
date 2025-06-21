import asyncio
import time
from typing import Any, Callable, TypeVar, Optional, Awaitable
from functools import wraps
from app.utils.logging import get_logger

T = TypeVar('T')
logger = get_logger(__name__)


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: The async function to retry
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each failure
        exceptions: Tuple of exceptions to catch and retry on
    
    Returns:
        The result of the function call
    
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts - 1:
                logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                raise e
            
            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
            await asyncio.sleep(current_delay)
            current_delay *= backoff
    
    # This should never be reached due to the logic above, but add fallback
    raise last_exception or Exception("Retry function failed unexpectedly")


def measure_time(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def calculate_confidence_level(confidence: float) -> str:
    """Calculate confidence level category."""
    if confidence >= 0.9:
        return "high"
    elif confidence >= 0.7:
        return "medium"
    else:
        return "low"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250 - len(ext)] + ('.' + ext if ext else '')
    return filename


async def validate_file_type(filename: str, allowed_extensions: list) -> bool:
    """Validate file type based on extension."""
    if not filename:
        return False
    
    extension = filename.lower().split('.')[-1]
    return extension in [ext.lower() for ext in allowed_extensions]


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self) -> bool:
        """Check if a call can be made within rate limits."""
        now = time.time()
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False
    
    def reset(self):
        """Reset the rate limiter."""
        self.calls = []
