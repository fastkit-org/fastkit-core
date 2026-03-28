from typing import Literal, Callable
from starlette.requests import Request


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

    @classmethod
    def _per_to_seconds(cls, per: Literal['second', 'minute', 'hour', 'day']) -> int:
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
        pass