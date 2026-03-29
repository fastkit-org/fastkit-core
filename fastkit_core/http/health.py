from typing import Literal

from pydantic import BaseModel

class HealthCheck(BaseModel):
    name: str
    status: Literal['ok', 'error', 'degraded']
    detail: str | None = None
    latency_ms: int | None = None