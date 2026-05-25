"""
Error Handling & Resilience Module
Provides retry logic, circuit breaker, and graceful degradation
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Optional, Type
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Implements circuit breaker pattern to prevent cascading failures
    States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing) -> CLOSED
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        name: str = "CircuitBreaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.warning(
                    f"[{self.name}] Circuit breaker entering HALF_OPEN state",
                    extra={"state": self.state}
                )
            else:
                raise CircuitBreakerError(
                    f"[{self.name}] Circuit breaker OPEN - too many failures"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info(
                f"[{self.name}] Circuit breaker closed - recovery successful",
                extra={"state": self.state}
            )
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        logger.error(
            f"[{self.name}] Failure detected",
            extra={
                "failure_count": self.failure_count,
                "threshold": self.failure_threshold
            }
        )
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.critical(
                f"[{self.name}] Circuit breaker OPEN - too many failures",
                extra={
                    "state": self.state,
                    "failures": self.failure_count
                }
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1,
    max_delay: float = 60,
    exponential_base: float = 2,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retry logic with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(
                        f"[{func.__name__}] Attempt {attempt + 1}/{max_retries + 1}",
                        extra={"attempt": attempt + 1}
                    )
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"[{func.__name__}] All retry attempts failed",
                            extra={
                                "attempts": attempt + 1,
                                "error": str(e)
                            },
                            exc_info=True
                        )
                        raise
                    
                    # Calculate backoff with jitter
                    import random
                    jitter = random.uniform(0, 0.1 * delay)
                    wait_time = min(delay + jitter, max_delay)
                    
                    logger.warning(
                        f"[{func.__name__}] Retry after {wait_time:.2f}s",
                        extra={
                            "attempt": attempt + 1,
                            "delay": wait_time,
                            "error": str(e)
                        }
                    )
                    
                    time.sleep(wait_time)
                    delay = min(delay * exponential_base, max_delay)
            
            raise last_exception or Exception("Unknown error in retry logic")
        
        return wrapper
    return decorator


def circuit_breaker_decorator(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    name: Optional[str] = None
):
    """Decorator to apply circuit breaker to a function"""
    
    def decorator(func: Callable) -> Callable:
        cb = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            name=name or func.__name__
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator


def safe_call(
    func: Callable,
    *args,
    default_return: Any = None,
    log_error: bool = True,
    error_prefix: str = "Error calling function",
    **kwargs
) -> Any:
    """
    Safely call a function with graceful error handling
    
    Args:
        func: Function to call
        default_return: Value to return on error
        log_error: Whether to log the error
        error_prefix: Prefix for error message
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(
                f"{error_prefix}: {func.__name__}",
                extra={"error": str(e)},
                exc_info=True
            )
        return default_return
