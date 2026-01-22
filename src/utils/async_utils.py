#!/usr/bin/env python3

"""
Async and concurrency utilities for Grok Assistant.

Provides utilities for responsive interrupt handling in long-running operations.
"""

import time
from typing import Callable, Optional


class InterruptedError(Exception):
    """Raised when an interruptible operation is cancelled."""
    pass


def interruptible_sleep(
    seconds: float,
    check_interval: float = 0.1,
    interrupt_check: Optional[Callable[[], bool]] = None
) -> bool:
    """
    Sleep for specified duration while remaining responsive to KeyboardInterrupt.

    Instead of blocking for the full duration, breaks the sleep into small
    intervals and checks for interrupts between them. This ensures the user
    can cancel a runaway orchestration immediately.

    Args:
        seconds: Total duration to sleep in seconds
        check_interval: How often to check for interrupts (default: 0.1s)
        interrupt_check: Optional callback that returns True if should interrupt

    Returns:
        True if sleep completed normally, False if interrupted via callback

    Raises:
        KeyboardInterrupt: If user presses Ctrl+C during sleep

    Example:
        >>> # Sleep for 1 second, checking every 0.1s for Ctrl+C
        >>> interruptible_sleep(1.0)

        >>> # Sleep with custom interrupt condition
        >>> should_stop = False
        >>> interruptible_sleep(5.0, interrupt_check=lambda: should_stop)
    """
    if seconds <= 0:
        return True

    # Ensure check_interval is reasonable
    check_interval = min(check_interval, seconds)
    check_interval = max(check_interval, 0.01)  # At least 10ms

    elapsed = 0.0
    while elapsed < seconds:
        # Check for custom interrupt condition
        if interrupt_check is not None and interrupt_check():
            return False

        # Calculate sleep duration for this iteration
        remaining = seconds - elapsed
        sleep_duration = min(check_interval, remaining)

        # This will raise KeyboardInterrupt if Ctrl+C is pressed
        time.sleep(sleep_duration)

        elapsed += sleep_duration

    return True


class InterruptiblePoller:
    """
    A context manager for interruptible polling operations.

    Provides a clean interface for polling with timeout while remaining
    responsive to user interrupts.

    Example:
        >>> with InterruptiblePoller(timeout=60, poll_interval=2) as poller:
        ...     while not poller.should_stop():
        ...         result = check_for_result()
        ...         if result:
        ...             break
        ...         poller.wait()
    """

    def __init__(
        self,
        timeout: float,
        poll_interval: float = 1.0,
        check_interval: float = 0.1
    ):
        """
        Initialize the interruptible poller.

        Args:
            timeout: Maximum time to poll in seconds
            poll_interval: Time between poll attempts
            check_interval: How often to check for KeyboardInterrupt within poll_interval
        """
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.check_interval = check_interval
        self._start_time: Optional[float] = None
        self._interrupted = False
        self._attempts = 0

    def __enter__(self) -> 'InterruptiblePoller':
        self._start_time = time.time()
        self._interrupted = False
        self._attempts = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Don't suppress exceptions
        return False

    def elapsed(self) -> float:
        """Return elapsed time since polling started."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def remaining(self) -> float:
        """Return remaining time before timeout."""
        return max(0.0, self.timeout - self.elapsed())

    def timed_out(self) -> bool:
        """Check if timeout has been reached."""
        return self.elapsed() >= self.timeout

    def should_stop(self) -> bool:
        """Check if polling should stop (timeout or interrupt)."""
        return self._interrupted or self.timed_out()

    @property
    def attempts(self) -> int:
        """Return number of poll attempts made."""
        return self._attempts

    def wait(self) -> bool:
        """
        Wait for poll_interval while checking for interrupts.

        Returns:
            True if wait completed normally, False if interrupted

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C
        """
        self._attempts += 1

        # Don't wait longer than remaining time
        actual_interval = min(self.poll_interval, self.remaining())

        if actual_interval <= 0:
            return True

        def check_timeout():
            return self.timed_out()

        return interruptible_sleep(
            actual_interval,
            check_interval=self.check_interval,
            interrupt_check=check_timeout
        )

    def interrupt(self) -> None:
        """Signal that polling should stop."""
        self._interrupted = True
