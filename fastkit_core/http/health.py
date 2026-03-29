from typing import Literal, List

from fastapi import APIRouter
from pydantic import BaseModel
from fastkit_core.database import health_check_all, health_check_all_async

class HealthCheck(BaseModel):
    name: str
    status: Literal['ok', 'error', 'degraded']
    detail: str | None = None
    latency_ms: int | None = None

def check_databases() -> List[HealthCheck]:
    results = []
    for name, items in health_check_all().items():
        results.append(HealthCheck(
            name=name,
            status = 'error' if 'error' in items else 'ok',
            detail = items.__str__()
        ))
    return results