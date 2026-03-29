from typing import Literal, List, Optional
import asyncio
import time
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from fastkit_core.database import health_check_all, health_check_all_async

class HealthCheck(BaseModel):
    name: str
    status: Literal['ok', 'error', 'degraded']
    detail: Optional[str] = None
    latency_ms: Optional[int] = None

class HealthResponse(BaseModel):
    status: str
    version: Optional[str] = None
    checks: List[HealthCheck] = Field(default_factory=list)

def check_databases() -> List[HealthCheck]:
    results = []
    for name, items in health_check_all().items():
        results.append(HealthCheck(
            name = f"database:{name}",
            status = 'error' if 'error' in items else 'ok',
            detail = items.__str__()
        ))
    return results

async def check_async_databases() -> List[HealthCheck]:
    results = []
    for name, items in await health_check_all_async().items():
        results.append(HealthCheck(
            name = f"database:{name}",
            status = 'error' if 'error' in items else 'ok',
            detail = items.__str__()
        ))
    return results

