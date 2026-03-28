import time
from typing import Literal, Callable
from starlette.requests import Request
from fastkit_core.http import TooManyRequestsException


class RateLimit:

    def __init__(
            self,
            limit: int,
            per: Literal['second', 'minute', 'hour', 'day'],
            key_func: Callable[[Request], str] | None = None,
    ):
        self.limit = limit
        self.per = per
        self.key_func = key_func
        self._window_seconds = self._per_to_seconds(per)
        self._prefix = f"rl:{limit}:{per}:"
        self._storage: dict[str, tuple[int, float]] = {}

    @staticmethod
    def _per_to_seconds(per: Literal['second', 'minute', 'hour', 'day']) -> int:
        match per:
            case 'second':
                return 1
            case 'minute':
                return 60
            case 'hour':
                return  60**2
            case 'day':
                return 60**2 * 24
            case _:
                return 1


    def _get_key(self, request: Request) -> str:
        if self.key_func is not None:
            return f"{self._prefix}{self.key_func(request)}"

        # X-Forwarded-For za apps iza proxy-ja
        forwarded_for = request.headers.get('X-Forwarded-For')
        ip = forwarded_for.split(',')[0].strip() if forwarded_for else request.client.host

        return f"{self._prefix}{ip}"

    async def __call__(self, request: Request) -> None:
        """
        FastAPI dependency. Raises HTTP 429 if limit exceeded.
        Can be used directly with Depends() or stored as a variable.
        """
        key = self._get_key(request)
        now = time.time()
        count, window_start = self._storage.get(key, (0, now))

        if now - window_start >= self._window_seconds:
            count, window_start = 0, now

        count += 1
        self._storage[key] = (count, window_start)

        if count > self.limit:
            retry_after = int(window_start + self._window_seconds - now)
            raise TooManyRequestsException(
                message= f'Too many requests. Please try again in {retry_after} seconds.',
                headers={
                            'Retry-After': str(retry_after),
                            'X-RateLimit-Limit': str(self.limit),
                            'X-RateLimit-Remaining': '0',
                            'X-RateLimit-Reset': str(int(window_start + self._window_seconds)),
                        }
            )