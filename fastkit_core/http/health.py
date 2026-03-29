from typing import Literal, List, Optional, Callable, Awaitable
import asyncio
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from fastkit_core.database import health_check_all, health_check_all_async
from starlette.responses import JSONResponse
import importlib.metadata
from functools import lru_cache

@lru_cache
def get_version() -> str:
    try:
        return importlib.metadata.version("fastkit-core")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-unknown"

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
            status = 'error' if not all(items.values()) else 'ok',
            detail = items.__str__()
        ))
    return results

async def check_async_databases() -> List[HealthCheck]:
    results = []
    checks = await health_check_all_async()
    for name, items in checks.items():
        results.append(HealthCheck(
            name = f"database:{name}",
            status = 'error' if not all(items.values()) else 'ok',
            detail = items.__str__()
        ))
    return results


def create_health_router(
        checks: list[Callable[[], Awaitable[HealthCheck]]] | None = None,
        include_db: bool = True,
        include_version: bool = True,
        liveness_path: str = '/',
        readiness_path: str = '/ready',
        is_db_async: bool = True,
) -> APIRouter:
    router = APIRouter()
    custom_checks = checks or []
    app_version = get_version() if include_version else None

    @router.get(liveness_path)
    async def liveness():
        return HealthResponse(status="ok", version=app_version)

    @router.get(readiness_path)
    async def readiness():
        all_results = []
        if custom_checks:
            all_results = list(await asyncio.gather(*(c() for c in custom_checks)))

        if include_db:

            if is_db_async:
                db_results = await check_async_databases()
            else:
                db_results = check_databases()

            all_results.extend(db_results)

        is_failed = any(r.status == 'error' for r in all_results)

        response = HealthResponse(
            status="error" if is_failed else "ok",
            checks=[r.model_dump() for r in all_results],
            version=app_version
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE if is_failed else status.HTTP_200_OK,
            content=response.model_dump()
        )

    return router
