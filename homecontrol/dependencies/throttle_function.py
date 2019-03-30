from functools import wraps
import time


class throttle(object):
    """
    Throttles a function so it only gets called at a fixed frequency
    """
    def __init__(self, s: float = 1):
        self.throttle_period = s
        self.time_of_last_call = time.time()

    def __call__(self, fn: callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = time.time()

            if now - self.time_of_last_call > self.throttle_period:
                self.time_of_last_call = now
                return fn(*args, **kwargs)

        return wrapper
