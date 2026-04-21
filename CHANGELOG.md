# Changelog

All notable changes to FastKit Core are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
FastKit Core follows [Semantic Versioning](https://semver.org/).

---

## [0.4.1] — 2026-04-21

This release eliminates sync/async code duplication in the repository layer,
adds missing feature parity between the two implementations, and introduces
automatic Pydantic and SQLAlchemy serialization in HTTP response helpers.
No breaking changes.

### Changed

#### Repository — Shared Base Logic (`fastkit_core/database/base_repository.py`)

Extracted all non-I/O logic from `Repository` and `AsyncRepository` into a shared
`_BaseRepositoryMixin`. Both classes now inherit the same query-building helpers
and only differ in session type and `await` usage.

- **`_parse_field_operator()`** — moved from both repository classes into the mixin.
  Single source of truth for Django-style `field__operator` parsing.
- **`_has_soft_delete()`** and **`query()`** — moved into the mixin. Eliminates
  identical method declarations in both classes.
- **`_build_pagination_meta()`** — new shared method. Calculates `total_pages`,
  `has_next`, and `has_prev` from `page`, `per_page`, and `total`. Both `paginate()`
  implementations now delegate to this method instead of constructing the dict inline.

#### Repository — Feature Parity

- **`filter_or()`** added to `AsyncRepository`. Previously only available on the sync
  `Repository`. Supports OR groups, AND conditions, `_load_relations`, and `_order_by`
  — identical API to the sync version.
- **`filter_or()`** in `Repository` — fixed incomplete implementation. `and_filters`
  keyword arguments were accepted but silently ignored. Now correctly applied as
  AND conditions on top of the OR clause. Added `_load_relations` and `_order_by`
  support consistent with other read methods.
- **`delete_many()`** in `Repository` — added missing `force: bool = False` parameter.
  Previously always performed a hard delete, ignoring soft delete even when available.
  Now consistent with `AsyncRepository.delete_many()` and `Repository.delete()`.

#### HTTP Responses — Automatic Serialization (`fastkit_core/http/responses.py`)

- **`_serialize()`** — extended with recursive serialization and two new fallbacks:
  - **SQLAlchemy model fallback** — objects with `__table__` are serialized to a
    plain `dict` of column values. Passing ORM instances directly to `success_response()`
    or `paginated_response()` no longer raises `TypeError`.
  - **Recursive dict/list handling** — nested Pydantic models, ORM instances, or mixed
    structures inside `dict` and `list` values are now fully serialized. Previously only
    the top-level object was processed.

### Fixed

- `filter_or()` in `Repository` silently dropped all `**and_filters` keyword arguments.
- `delete_many()` in `Repository` always performed a hard delete, bypassing soft delete.
- `_serialize()` raised `TypeError` when passed a SQLAlchemy model instance directly.
- `_serialize()` did not recurse into `dict` or `list` values, leaving nested objects
  unserializable.

## [0.4.0] — 2026-04-11

This release focuses on infrastructure that every production application needs but
typically implements from scratch on every project: caching, rate limiting, health checks,
and event-driven communication between modules. All additions are backward compatible —
existing code requires no changes.

### Added

#### Caching Layer (`fastkit_core/cache/`)

A unified, backend-agnostic caching layer with zero required new dependencies.

- **`InMemoryBackend`** — in-process dict storage, lazy TTL expiry, wildcard pattern invalidation via `fnmatch`. Works out of the box with no additional install.
- **`RedisBackend`** — fully async Redis client via `redis.asyncio`. TTL delegated to Redis natively. Available via `pip install fastkit-core[redis]`.
- **`CacheManager`** — singleton interface that delegates to the configured backend. Initialize once at startup with `setup_cache(config)`, then import the `cache` proxy anywhere.
- **`cache` proxy** — module-level lazy proxy (`from fastkit_core.cache import cache`) eliminates the need for explicit `get_cache()` calls throughout application code.
- **`@cached` decorator** — cache async function results with a single line. Accepts a static string key or a `Callable[..., str]` lambda for dynamic keys derived from function arguments. Enforces async-only usage at decoration time.
- **TTL control** at three levels: config default, per-call override, and no-expiry (`ttl=None`).
- **Pattern invalidation** (`cache.invalidate('users:*')`) — clears entire key namespaces in one call.

```python
from fastkit_core.cache import cache, cached

await cache.set('users:all', users, ttl=300)
data = await cache.get('users:all')
await cache.invalidate('users:*')

@cached(ttl=60, key=lambda user_id: f'user:{user_id}')
async def get_user(user_id: int) -> UserResponse: ...
```

---

#### Multi-Field Ordering for Repository and Service Layer

Extended `_order_by` to accept a list of fields in addition to a single string. Applied
across all read methods on both sync and async classes.

- **`_order_by`** now accepts `str | list[str]` in `filter()`, `get_all()`, `first()`, and `paginate()` on `Repository`, `AsyncRepository`, `BaseCrudService`, and `AsyncBaseCrudService`.
- Prefix `-` for descending, no prefix for ascending — consistent with existing single-field behaviour.
- Fields are applied left-to-right. Unknown or invalid field names are silently ignored.
- Fully backward compatible — single string usage is unchanged.

```python
# Two fields — newest first, then alphabetical
items = await repo.filter(
    status='active',
    _order_by=['-created_at', 'name']
)

# Three fields with pagination
items, meta = service.paginate(
    page=1, per_page=20,
    _order_by=['-priority', 'due_date', 'name']
)
```

---

#### Cursor-Based Pagination (`cursor_paginate`)

Added `cursor_paginate()` as a performant alternative to offset-based `paginate()` for
large datasets and feed-style endpoints.

- Available on `Repository`, `AsyncRepository`, `BaseCrudService`, and `AsyncBaseCrudService`.
- Uses the **`per_page + 1` trick** to detect last page without a `COUNT(*)` query.
- Cursor is a **URL-safe base64-encoded** string — opaque to the client, safe to pass as a query parameter.
- `datetime` cursor values are serialized to ISO 8601 automatically.
- Supports all existing Django-style filter operators (`field__gte`, `field__in`, etc.).
- `cursor_field` defaults to `id`; any indexed column can be used.
- Ordering is implicit from `cursor_field` + `direction` — no separate `_order_by` parameter to avoid cursor inconsistency.
- Response schema mapping applied automatically at service layer — returns `list[ResponseSchema]`, not raw model instances.

```python
# First page
items, next_cursor = await repo.cursor_paginate(per_page=20)

# Next page
items, next_cursor = await repo.cursor_paginate(
    per_page=20,
    cursor=next_cursor,
    cursor_field='created_at',
    direction='desc',
    status='active'
)

# next_cursor is None on the last page
```

---

#### Signal / Event System (`fastkit_core/events/`)

A lightweight, in-process signal system for decoupling side effects and cross-module
communication. Designed for forward compatibility with broker backends planned for 0.5.0.

- **`Signal(name)`** — module-level signal instance. Receivers connect to the object, not the name string.
- **`@signal.connect`** — decorator that registers async or sync receivers. Returns the receiver unchanged.
- **`await signal.send(payload)`** — always async, even in-process, for forward compatibility with 0.5.0 broker backends.
- **Error isolation** — a receiver exception is caught, logged with full traceback, and never propagates to the sender or to other receivers. All receivers always run.
- **`signal.disconnect(receiver)`** — explicit unregistration.
- **`signal.connected_to(receiver)`** — context manager for temporary connections; receiver is disconnected on exit even if an exception is raised. Primarily useful in tests.
- **`BaseSignalBackend`** — abstract backend class already present in `backends/base.py`, making the 0.5.0 broker backend a purely additive change.
- **`InProcessBackend`** — default backend; dispatches receivers in registration order within the current process.
- **Payload warning** — a `UserWarning` is emitted at send time if the payload is not a `dict`, `dataclass`, or Pydantic model, signaling that the payload will not survive broker serialization in 0.5.0.

```python
# users/signals.py
from fastkit_core.events import Signal

user_created = Signal('user.created')
user_deleted = Signal('user.deleted')

# users/listeners.py
from .signals import user_created

@user_created.connect
async def send_welcome_email(payload: dict) -> None:
    await email_service.send_welcome(payload['email'])

# users/service.py
async def after_create(self, instance: User) -> None:
    await user_created.send({'id': instance.id, 'email': instance.email})
```

---

#### `BaseSchema` Improvements — `BaseCreateSchema`, `BaseUpdateSchema`, Serialization Helpers

Extended the validation base classes to standardize create/update/response schema patterns.

- **`BaseSchema`** — `from_attributes=True` enabled by default via `model_config`. ORM instances can now be passed directly to `model_validate()` without explicit config on every subclass.
- **`BaseCreateSchema`** — new base class for POST request bodies. Sets `extra='forbid'` (returns `422` on unexpected fields) and auto-strips leading/trailing whitespace from all string fields via `@field_validator('*', mode='before')`.
- **`BaseUpdateSchema`** — new base class for PATCH request bodies. Sets `extra='forbid'`. Convention: all fields declared as `Optional` with `None` default so only explicitly provided fields are written to the database.
- **`to_dict(exclude_none)`** — convenience wrapper over `model_dump()` available on all `BaseSchema` subclasses.
- **`to_json_str(exclude_none)`** — convenience wrapper over `model_dump_json()`.
- **`config_exclude_none()`** and **`config_exclude_fields(fields)`** — class methods that return `ConfigDict` and serve as documentation anchors communicating serialization intent. (Pydantic v2 does not support exclusion at `ConfigDict` level; actual exclusion uses `to_dict(exclude_none=True)` or `Field(exclude=True)`.)

```python
class UserCreate(BaseCreateSchema):
    name: str       # whitespace stripped, extra fields forbidden
    email: str

class UserUpdate(BaseUpdateSchema):
    name: str | None = None   # only sent fields are updated
    email: str | None = None

class UserResponse(BaseSchema):
    id: int
    name: str
    # from_attributes=True already set — works with ORM instances directly
```

---

#### Rate Limiting (`fastkit_core/http/rate_limit.py`)

A FastAPI `Depends()`-based rate limiter with zero required new dependencies.

- **`RateLimit(limit, per, key_func)`** — callable class that implements FastAPI's dependency protocol. Use with `Depends()` at router or endpoint level.
- **Fixed-window algorithm** with in-memory per-instance storage.
- **Default key** is client IP from `request.client.host` with `X-Forwarded-For` header support.
- **`key_func`** — optional callable `(request) -> str` for per-user, per-API-key, or any custom rate limiting strategy.
- Raises **`TooManyRequestsException`** (HTTP 429) with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers. Response body uses FastKit's standard `error_response()` format.
- **`TooManyRequestsException`** added to the exceptions hierarchy, inheriting from `FastKitException`. The global exception handler passes its `headers` to the `JSONResponse` automatically.

```python
# Router-level — one line covers all endpoints
auth_router = APIRouter(
    dependencies=[Depends(RateLimit(10, per='minute'))]
)

# Per-user rate limiting
@app.post('/export')
async def export(_: None = Depends(RateLimit(
    10, per='day',
    key_func=lambda req: req.state.user_id
))):
    ...
```

---

#### Standardized Health Check Router (`fastkit_core/http/health.py`)

A `create_health_router()` factory that generates a ready-to-mount `APIRouter` with
liveness and readiness endpoints.

- **`GET /health/`** — liveness probe. Always returns `200 OK` while the process is running. No checks performed.
- **`GET /health/ready`** — readiness probe. Runs all registered checks. Returns `200 OK` if all pass, `503 Service Unavailable` if any check has `status='error'`.
- **`HealthCheck`** Pydantic model: `name`, `status` (`'ok' | 'error' | 'degraded'`), `detail`, `latency_ms`.
- **`HealthResponse`** Pydantic model: `status`, `version` (from `importlib.metadata`, cached with `@lru_cache`), `checks`.
- **Custom checks** registered as async callables that return `HealthCheck`. Database check included by default via existing `health_check_all()`.
- **`include_db`**, **`include_version`**, **`is_db_async`**, **`liveness_path`**, **`readiness_path`** parameters for full customization.

```python
app.include_router(
    create_health_router(
        checks=[redis_check, stripe_check],
        is_db_async=True,
    ),
    prefix='/health',
    tags=['Health']
)
```

---

### Changed

- **`FastKitException.__init__`** — added `headers` parameter. The global `fastkit_exception_handler` and `error_response()` now pass `headers` through to the `JSONResponse`. This is a non-breaking additive change used internally by `TooManyRequestsException`.

---

### Infrastructure

- **CI workflow** (`test_publish.yaml`) — replaced single-trigger tag-only workflow with a two-trigger setup: tests run on every push and PR to `main` and `development`; publish job runs only on `v*.*.*` tags and only after tests pass (`if: startsWith(github.ref, 'refs/tags/v')`).
- **Test matrix** — CI now runs tests on Python 3.11 and 3.12 in parallel using `strategy.matrix`.
- **`ci` optional extra** — added to `pyproject.toml` with the exact dependencies needed for CI: pytest stack, aiosqlite, asyncpg, redis. Replaces `--all-extras` in CI to avoid system-level database drivers (Oracle, MSSQL, ODBC) that are not available on GitHub Actions runners.
- **`[project.urls]`** — updated from `codevelo-pub` GitHub org to `fastkit-org` and `fastkit.org`.

---

### Deferred to 0.5.0

The following items were scoped, designed, and partially prototyped during 0.4.0 planning
but deliberately deferred to keep this release focused:

- **Async Event Bus with swappable broker backends** — `RabbitMQBackend`, `RedisStreamsBackend`, at-least-once delivery, dead letter queue, retry logic. The `BaseSignalBackend` abstract class introduced in 0.4.0 makes this a purely additive change.
- **`BaseRepository` abstract class** — to eliminate shared code duplication between `Repository` and `AsyncRepository` (`LOOKUP_OPERATORS`, helper methods, cursor encoding). Public API will remain identical.
- **Cursor pagination Redis backend** — for distributed cursor state across workers.

---

## [0.3.5] — Previous release

See git history for changes prior to 0.4.0.
