# Database

- [Introduction](#introduction)
- [Quick Start](#quick-start)
- [Base Models](#base-models)
- [Mixins](#mixins)
- [Session Management](#session-management)
- [Repository Pattern](#repository-pattern)
- [Async Support](#async-support)
- [TranslatableMixin](#translatablemixin)
- [Connection Manager](#connection-manager)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's database module provides a powerful, production-ready foundation for working with databases. Built on SQLAlchemy 2.0+, it adds useful patterns and features while staying close to SQLAlchemy's flexibility.

**Key Features:**

- **Base Models** - Auto table names, serialization, relationships
- **Rich Mixins** - IntId, UUID, soft delete, timestamps, slugs, publishing
- **Multi-language Models** - TranslatableMixin for i18n content
- **Repository Pattern** - Clean data access layer with Django-style filters
- **Multi-Field Ordering** - Order by multiple fields with ASC/DESC per field
- **Async/Sync Support** - Full async support with feature parity
- **Read Replicas** - Automatic read/write splitting
- **Connection Manager** - Handle multiple databases
- **Multi-Database Support** - PostgreSQL, MySQL, MariaDB, MSSQL, Oracle, SQLite
- **FastAPI Integration** - Dependency injection ready with modern lifespan events

**Supported Databases:**
- PostgreSQL (sync: psycopg2, async: asyncpg)
- MySQL (sync: pymysql, async: aiomysql)
- MariaDB (sync: pymysql, async: aiomysql)
- MSSQL (sync: pyodbc, async: aioodbc)
- Oracle (sync: cx_oracle, async: oracledb)
- SQLite (sync only)

---

<a name="quick-start"></a>
## Quick Start

### Installation

```bash
# Basic installation
pip install fastkit-core

# With PostgreSQL async support
pip install fastkit-core[postgresql-async]

# With MySQL async support
pip install fastkit-core[mysql-async]
```

### Define Models

```python
from fastkit_core.database import Base, IntIdMixin, TimestampMixin, SoftDeleteMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

class User(Base, IntIdMixin, TimestampMixin, SoftDeleteMixin):
    """User model with ID, timestamps, and soft delete."""
    __tablename__ = 'users'  # Optional - auto-generated as 'users'

    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
```

### Initialize Database

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastkit_core.database import init_database, shutdown_database
from fastkit_core.config import ConfigManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = ConfigManager()
    init_database(config)

    # Create tables
    from fastkit_core.database import get_db_manager
    Base.metadata.create_all(get_db_manager().engine)

    yield

    # Shutdown
    shutdown_database()

app = FastAPI(lifespan=lifespan)
```

### Use with FastAPI

```python
from fastapi import Depends
from fastkit_core.database import Repository, get_db
from sqlalchemy.orm import Session

@app.get("/users")
def list_users(session: Session = Depends(get_db)):
    repo = Repository(User, session)
    users = repo.get_all(limit=10)
    return [user.to_dict() for user in users]

@app.post("/users")
def create_user(user_data: dict, session: Session = Depends(get_db)):
    repo = Repository(User, session)
    user = repo.create(user_data)
    return user.to_dict()
```

---

<a name="base-models"></a>
## Base Models

### Base

The foundation for all models with auto table names and serialization.

```python
from fastkit_core.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

class Product(Base):
    """Product model - table name auto-generated as 'products'."""
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[float]
```

**Auto table name generation:**
- `User` → `users`
- `UserProfile` → `user_profiles`
- `Category` → `categories`
- `Address` → `addresses`

**Override table name:**
```python
class Product(Base):
    __tablename_override__ = 'custom_products'
    name: Mapped[str]
```

**Serialization:**
```python
product = Product(name="Widget", price=9.99)

# To dictionary
data = product.to_dict()
# {'id': 1, 'name': 'Widget', 'price': 9.99}

# Exclude fields
data = product.to_dict(exclude=['price'])
# {'id': 1, 'name': 'Widget'}

# Include relationships
data = product.to_dict(include_relationships=True, max_depth=2)
# {'id': 1, 'name': 'Widget', 'price': 9.99, 'category': {...}}

# Update from dict
product.update_from_dict({'name': 'Super Widget', 'price': 12.99})

# Allow only specific fields
product.update_from_dict(
    {'name': 'New Name', 'price': 99.99, 'hack': 'value'},
    allow_only=['name', 'price']
)
```

**Custom repr:**
```python
class User(Base):
    name: Mapped[str]
    email: Mapped[str]

    def __repr_attrs__(self):
        return [('id', self.id), ('name', self.name), ('email', self.email)]

# Output: <User(id=1, name='John', email='john@test.com')>
```

### BaseWithTimestamps

Convenience base with timestamps included:

```python
from fastkit_core.database import BaseWithTimestamps

class Article(BaseWithTimestamps):
    """Automatically includes id, created_at and updated_at."""
    title: Mapped[str]
    content: Mapped[str]

# Automatically has:
# - id (from Base)
# - created_at (from TimestampMixin)
# - updated_at (from TimestampMixin)
```

---

<a name="mixins"></a>
## Mixins

FastKit Core provides reusable mixins for common patterns.

### IntIdMixin

Auto-incrementing integer primary key:

```python
from fastkit_core.database import Base, IntIdMixin

class User(Base, IntIdMixin):
    name: Mapped[str]

# Automatically has:
# id: Mapped[int] - auto-incrementing primary key
```

### UUIDMixin

UUID primary key for distributed systems:

```python
from fastkit_core.database import Base, UUIDMixin

class User(Base, UUIDMixin):
    name: Mapped[str]

user = User(name="Alice")
print(user.id)  # UUID('550e8400-e29b-41d4-a716-446655440000')
```

**When to use:** distributed systems, public-facing IDs, security (non-sequential).

### TimestampMixin

Automatic created_at and updated_at timestamps:

```python
from fastkit_core.database import Base, IntIdMixin, TimestampMixin

class Post(Base, IntIdMixin, TimestampMixin):
    title: Mapped[str]

post = Post(title="Hello")
session.add(post)
session.commit()

print(post.created_at)  # 2025-01-10 10:30:00
print(post.updated_at)  # 2025-01-10 10:30:00

# updated_at is auto-updated on every save
post.title = "Hello World"
session.commit()
print(post.updated_at)  # 2025-01-10 10:35:00
```

### SoftDeleteMixin

Soft delete support (mark as deleted instead of removing):

```python
from fastkit_core.database import Base, IntIdMixin, SoftDeleteMixin

class Post(Base, IntIdMixin, SoftDeleteMixin):
    title: Mapped[str]

# Soft delete
post.soft_delete()
print(post.is_deleted)  # True

# Restore
post.restore()
print(post.is_deleted)  # False

# Query helpers
active_posts = Post.active(session).all()      # Only non-deleted
deleted_posts = Post.deleted(session).all()    # Only deleted
all_posts = Post.with_deleted(session).all()   # Including deleted
```

Repository methods automatically exclude soft-deleted records from all queries.
Use `force=True` on `delete()` to bypass soft delete and remove the record permanently.

### SlugMixin

URL-friendly slug field. To generate the slug value automatically, use `SlugServiceMixin` in your service layer.

```python
from fastkit_core.database import Base, IntIdMixin, SlugMixin

class Post(Base, IntIdMixin, SlugMixin):
    title: Mapped[str]

# Automatically has:
# slug: Mapped[str] - unique, indexed
```

### PublishableMixin

Publishing workflow (draft, published, scheduled):

```python
from fastkit_core.database import Base, IntIdMixin, PublishableMixin
from datetime import datetime, timedelta, timezone

class Article(Base, IntIdMixin, PublishableMixin):
    title: Mapped[str]

article = Article(title="News")

print(article.is_draft)       # True
print(article.is_published)   # False
print(article.is_scheduled)   # False

# Publish immediately
article.publish()

# Unpublish (make draft)
article.unpublish()

# Schedule for future
future = datetime.now(timezone.utc) + timedelta(days=7)
article.schedule(future)
print(article.is_scheduled)   # True

# Query helpers
published = Article.published(session).all()
drafts = Article.drafts(session).all()
scheduled = Article.scheduled(session).all()
```

---

<a name="session-management"></a>
## Session Management

### Configuration

```python
# config/database.py
CONNECTIONS = {
    'default': {
        'driver': 'postgresql',
        'host': 'localhost',
        'port': 5432,
        'database': 'myapp',
        'username': 'user',
        'password': 'secret',
        'pool_size': 5,
        'max_overflow': 10,
    },
    'read_replica_1': {
        'driver': 'postgresql',
        'host': 'replica1.example.com',
        'port': 5432,
        'database': 'myapp',
        'username': 'readonly',
        'password': 'secret',
    },
    # Direct URL
    'analytics': {
        'url': 'postgresql://user:pass@analytics-db:5432/analytics'
    },
    # SQLite
    'sqlite_db': {
        'driver': 'sqlite',
        'database': '/path/to/database.db'
    }
}
```

### Initialize Database

```python
from fastkit_core.database import init_database, shutdown_database
from fastkit_core.config import ConfigManager

config = ConfigManager()

# Simple
init_database(config)

# With read replicas
init_database(
    config,
    connection_name='default',
    read_replicas=['read_replica_1', 'read_replica_2']
)
```

### Using Sessions

```python
from fastkit_core.database import get_db_manager

db = get_db_manager()

# Write operation — auto-commits on success, rolls back on error
with db.session() as session:
    user = User(name="John")
    session.add(user)

# Read operation — uses read replicas if configured
with db.read_session() as session:
    users = session.query(User).all()
```

### FastAPI Dependency Injection

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from fastkit_core.database import get_db, get_read_db

@app.post("/users")
def create_user(data: dict, session: Session = Depends(get_db)):
    user = User(**data)
    session.add(user)
    session.commit()
    return user.to_dict()

@app.get("/users")
def list_users(session: Session = Depends(get_read_db)):
    return session.query(User).all()
```

### Health Checks

```python
from fastkit_core.database import health_check_all

health = health_check_all()
# {
#     'default': {
#         'primary': True,
#         'read_replica_1': True,
#         'read_replica_2': False
#     }
# }
```

---

<a name="repository-pattern"></a>
## Repository Pattern

The Repository pattern provides a clean abstraction over database operations.

### Basic Usage

```python
from fastkit_core.database import Repository, get_db
from fastapi import Depends
from sqlalchemy.orm import Session

def get_user_repo(session: Session = Depends(get_db)) -> Repository:
    return Repository(User, session)

@app.get("/users")
def list_users(repo: Repository = Depends(get_user_repo)):
    return [user.to_dict() for user in repo.get_all(limit=100)]
```

### CRUD Operations

**Create:**
```python
# Single record
user = repo.create({'name': 'John Doe', 'email': 'john@example.com'})

# Multiple records
users = repo.create_many([
    {'name': 'John', 'email': 'john@test.com'},
    {'name': 'Jane', 'email': 'jane@test.com'}
])

# Without auto-commit
user = repo.create({'name': 'John'}, commit=False)
repo.commit()
```

**Read:**
```python
user = repo.get(1)
user = repo.get_or_404(1)
users = repo.get_all()
users = repo.get_all(limit=100)
user = repo.first(email='john@test.com')
exists = repo.exists(email='john@test.com')
total = repo.count()
active_count = repo.count(status='active')
```

**Update:**
```python
user = repo.update(1, {'name': 'Jane Doe'})

count = repo.update_many(
    filters={'status': 'pending'},
    data={'status': 'active'}
)
```

**Delete:**
```python
deleted = repo.delete(1)             # Soft delete if model supports it
deleted = repo.delete(1, force=True) # Force hard delete
count = repo.delete_many({'status': 'inactive'})
```

### Filtering

Django-style filtering with operator support:

```python
users = repo.filter(status='active')
adults = repo.filter(age__gte=18, age__lt=65)
gmail_users = repo.filter(email__ilike='%@gmail.com')
names_starting_with_j = repo.filter(name__startswith='J')
active_users = repo.filter(status__in=['active', 'pending'])
users_without_email = repo.filter(email__is_null=True)
products = repo.filter(price__between=(10, 100))
```

**Available operators:** `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `in`, `not_in`, `like`, `ilike`, `is_null`, `is_not_null`, `between`, `startswith`, `endswith`, `contains`.

### Ordering

`_order_by` accepts a single field string or a list of fields. Prefix a field name with `-` for descending order.

```python
# Single field — ascending
users = repo.filter(_order_by='name')

# Single field — descending
users = repo.filter(_order_by='-created_at')

# Multiple fields — list syntax
# ORDER BY age ASC, name ASC
users = repo.filter(_order_by=['age', 'name'])

# Mixed directions
# ORDER BY status ASC, created_at DESC
users = repo.filter(_order_by=['status', '-created_at'])

# Three fields
tasks = repo.filter(_order_by=['-priority', 'due_date', 'name'])

# Works on all read methods
users = repo.get_all(_order_by=['-created_at', 'name'])
user = repo.first(_order_by='-score')
users, meta = repo.paginate(page=1, per_page=20, _order_by=['-created_at', 'name'])
```

Unknown or invalid field names in `_order_by` are silently ignored — the query still executes with the valid fields applied.

### Pagination

```python
users, meta = repo.paginate(page=1, per_page=20)

users, meta = repo.paginate(
    page=2,
    per_page=20,
    _order_by='-created_at',
    status='active',
    age__gte=18
)

print(meta)
# {
#     'page': 2,
#     'per_page': 20,
#     'total': 150,
#     'total_pages': 8,
#     'has_next': True,
#     'has_prev': True
# }
```

### Eager Loading (Preventing N+1)

Load related entities in a single query using SQLAlchemy `Load` objects.

```python
from sqlalchemy.orm import selectinload

# Without eager loading — N+1 problem
users = repo.get_all()
for user in users:
    print(user.posts)  # One query per user!

# With eager loading — 2 queries total
users = repo.get_all(load_relations=[selectinload(User.posts)])
for user in users:
    print(user.posts)  # Already loaded
```

**Multiple and nested relationships:**
```python
# Multiple relationships
invoice = repo.get(
    invoice_id,
    load_relations=[
        selectinload(Invoice.client),
        selectinload(Invoice.items),
        selectinload(Invoice.payments)
    ]
)

# Nested relationships
invoices = repo.get_all(load_relations=[
    selectinload(Invoice.client),
    selectinload(Invoice.items).selectinload(InvoiceItem.product),
])
```

**With filtering and pagination:**
```python
invoices = repo.filter(
    status='paid',
    _load_relations=[selectinload(Invoice.client), selectinload(Invoice.items)]
)

invoices, meta = repo.paginate(
    page=1, per_page=20,
    _load_relations=[selectinload(Invoice.client)]
)
```

**All methods that support eager loading:**
- `get(id, load_relations=None)`
- `get_or_404(id, load_relations=None)`
- `get_all(limit=None, load_relations=None, _order_by=None)`
- `filter(..., _load_relations=None, **filters)`
- `paginate(..., _load_relations=None, **filters)`
- `first(_load_relations=None, _order_by=None, **filters)`

### Transaction Management

```python
try:
    user = repo.create({'name': 'John'}, commit=False)
    profile = profile_repo.create({'user_id': user.id}, commit=False)
    repo.commit()  # Commit both or neither
except Exception:
    repo.rollback()
    raise

# Flush to get ID without committing
repo.create({'name': 'John'}, commit=False)
repo.flush()
print(user.id)  # Available after flush
```

### Custom Repository Methods

```python
from fastkit_core.database import Repository

class UserRepository(Repository):
    def get_active_users(self):
        return self.filter(status='active', deleted_at__is_null=True)

    def find_by_email(self, email: str):
        return self.first(email=email)

    def search_by_name(self, query: str):
        return self.filter(name__ilike=f'%{query}%')
```

---

<a name="async-support"></a>
## Async Support

### Async Session Management

```python
from fastkit_core.database import init_async_database
from fastkit_core.config import ConfigManager

config = ConfigManager()
init_async_database(config)
```

### FastAPI Async Dependency

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastkit_core.database import get_async_db, get_async_read_db

@app.post("/users")
async def create_user(data: dict, session: AsyncSession = Depends(get_async_db)):
    user = User(**data)
    session.add(user)
    await session.commit()
    return user.to_dict()

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_async_read_db)):
    result = await session.execute(select(User))
    return [u.to_dict() for u in result.scalars().all()]
```

### Async Repository

Full CRUD operations with async/await — identical API to `Repository`:

```python
from fastkit_core.database import AsyncRepository

repo = AsyncRepository(User, session)

user = await repo.create({'name': 'John', 'email': 'john@test.com'})
user = await repo.get(1)
user = await repo.get_or_404(1)
users = await repo.get_all(limit=100)
user = await repo.first(email='john@test.com')
exists = await repo.exists(email='john@test.com')
count = await repo.count(status='active')

# Filtering with operators — same syntax as sync
users = await repo.filter(
    status='active',
    age__gte=18,
    _limit=10,
    _order_by='-created_at'
)

# Multi-field ordering
users = await repo.filter(_order_by=['-created_at', 'name'])
users = await repo.get_all(_order_by=['department', '-score'])
users, meta = await repo.paginate(page=1, per_page=20, _order_by=['-priority', 'due_date'])

# Pagination
users, meta = await repo.paginate(page=1, per_page=20, status='active')

user = await repo.update(1, {'name': 'Jane'})
count = await repo.update_many({'status': 'pending'}, {'status': 'active'})
deleted = await repo.delete(1)
count = await repo.delete_many({'status': 'inactive'})
```

### Async Eager Loading

In async SQLAlchemy, **lazy loading does not work**. Always use `load_relations` for related data.

```python
from sqlalchemy.orm import selectinload

# ❌ This will fail in async — lazy loading unsupported
invoices = await repo.get_all()
for invoice in invoices:
    print(invoice.client.name)  # MissingGreenlet error!

# ✅ Correct — eager load everything you need
invoices = await repo.get_all(load_relations=[selectinload(Invoice.client)])
for invoice in invoices:
    print(invoice.client.name)  # Works
```

The API is identical to the sync version:

```python
# Single relationship
user = await repo.get(1, load_relations=[selectinload(User.posts)])

# Multiple relationships
invoice = await repo.get(
    invoice_id,
    load_relations=[
        selectinload(Invoice.client),
        selectinload(Invoice.items).selectinload(InvoiceItem.product),
    ]
)

# With filtering
invoices = await repo.filter(
    status='paid',
    _load_relations=[selectinload(Invoice.client)]
)

# With pagination
invoices, meta = await repo.paginate(
    page=1, per_page=20,
    _load_relations=[selectinload(Invoice.client)]
)
```

### Async Health Checks

```python
from fastkit_core.database import health_check_all_async

health = await health_check_all_async()
```

---

<a name="translatablemixin"></a>
## TranslatableMixin

Automatic multi-language support with zero boilerplate.

### Setup

```python
from fastkit_core.database import Base, IntIdMixin, TimestampMixin, TranslatableMixin
from sqlalchemy import JSON

class Article(Base, IntIdMixin, TimestampMixin, TranslatableMixin):
    __tablename__ = 'articles'
    __translatable__ = ['title', 'content']
    __fallback_locale__ = 'en'

    # Translatable fields MUST be JSON columns
    title: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)

    # Regular fields work normally
    author: Mapped[str] = mapped_column(String(100))
```

### Basic Usage

```python
article = Article(author="John")

article.title = "Hello World"        # Saves to current locale (en)

article.set_locale('es')
article.title = "Hola Mundo"         # Updates Spanish only

article.set_locale('en')
print(article.title)                 # "Hello World"
```

### Explicit Translation Management

```python
article.set_translation('title', 'Bonjour le monde', locale='fr')

title_es = article.get_translation('title', locale='es')
title_ja = article.get_translation('title', locale='ja', fallback=True)  # Falls back to 'en'

translations = article.get_translations('title')
# {'en': 'Hello World', 'es': 'Hola Mundo', 'fr': 'Bonjour le monde'}

has_spanish = article.has_translation('title', 'es')  # True
```

### FastAPI Integration

```python
from fastkit_core.database import set_locale_from_request

@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    locale = request.headers.get('Accept-Language', 'en')[:2]
    set_locale_from_request(locale)
    return await call_next(request)

@app.get("/articles/{article_id}")
def get_article(article_id: int, locale: str = 'en', session: Session = Depends(get_db)):
    repo = Repository(Article, session)
    article = repo.get(article_id)
    return article.to_dict(locale=locale)
```

---

<a name="connection-manager"></a>
## Connection Manager

Centralized manager for multiple database connections.

```python
from fastkit_core.database import ConnectionManager
from fastkit_core.config import ConfigManager

config = ConfigManager()
conn_manager = ConnectionManager(config)

conn_manager.add_connection('default', read_replicas=['read_replica_1', 'read_replica_2'])
conn_manager.add_connection('analytics', echo=True)

# Use different databases
primary_db = conn_manager.get('default')
analytics_db = conn_manager.get('analytics')

with primary_db.session() as session:
    user = User(name="John")
    session.add(user)

# Health check all
health = conn_manager.health_check_all()

# Management
conn_manager.list_connections()          # ['default', 'analytics']
conn_manager.has_connection('cache')
conn_manager.remove_connection('analytics')
conn_manager.dispose_all()               # Shutdown
```

---

<a name="advanced-features"></a>
## Advanced Features

### Relationships

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base, IntIdMixin, TimestampMixin):
    username: Mapped[str]
    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")

class Post(Base, IntIdMixin, TimestampMixin):
    title: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    author: Mapped["User"] = relationship(back_populates="posts")

# Serialize with relationships
user = repo.get(1)
data = user.to_dict(include_relationships=True, max_depth=2)
```

### Complex Queries

```python
query = repo.query()

from sqlalchemy import and_, or_
query = query.where(
    and_(
        User.age >= 18,
        or_(User.status == 'active', User.status == 'pending')
    )
)
result = session.execute(query)
users = result.scalars().all()
```

### Transactions with Multiple Repositories

```python
from fastkit_core.database import get_db_manager

db = get_db_manager()

with db.session() as session:
    try:
        user_repo = Repository(User, session)
        account_repo = Repository(Account, session)

        user = user_repo.create({'name': 'John'}, commit=False)
        account = account_repo.create({'user_id': user.id, 'balance': 0}, commit=False)

        session.commit()
    except Exception:
        session.rollback()
        raise
```

---

<a name="best-practices"></a>
## Best Practices

**Use mixins appropriately** — only add what the model actually needs. `LogEntry` does not need `SoftDeleteMixin` or `PublishableMixin`.

**Use the repository pattern** — keep database access in the repository, business logic in the service layer.

**Use dependency injection** — inject repositories via FastAPI `Depends()` rather than instantiating them in route handlers.

**Exclude sensitive fields on serialization** — always pass `exclude=['password']` or use response schemas in the service layer.

**Use read replicas for reads** — inject `get_read_db` for GET endpoints, `get_db` for write endpoints.

**Use async for I/O-bound operations** — prefer `AsyncRepository` and `get_async_db` in FastAPI async endpoints.

**Always eager load in async code** — lazy loading is not supported in async SQLAlchemy. Use `load_relations` whenever you need related data.

**Use transactions for related operations** — wrap multi-repository writes in a single transaction with `commit=False` and a manual `session.commit()`.

---

<a name="api-reference"></a>
## API Reference

### Repository / AsyncRepository

Both classes share an identical public interface. `AsyncRepository` methods are coroutines (use `await`).

```
# Create
create(data: dict, commit: bool = True) -> T
create_many(data_list: list[dict], commit: bool = True) -> list[T]

# Read
get(id, load_relations: Sequence[Load] | None = None) -> T | None
get_or_404(id, load_relations: Sequence[Load] | None = None) -> T
get_all(
    limit: int | None = None,
    load_relations: Sequence[Load] | None = None,
    _order_by: str | list[str] | None = None
) -> list[T]
first(
    _load_relations: Sequence[Load] | None = None,
    _order_by: str | list[str] | None = None,
    **filters
) -> T | None
filter(
    _limit: int | None = None,
    _offset: int | None = None,
    _order_by: str | list[str] | None = None,
    _load_relations: Sequence[Load] | None = None,
    **filters
) -> list[T]
paginate(
    page: int = 1,
    per_page: int = 20,
    _order_by: str | list[str] | None = None,
    _load_relations: Sequence[Load] | None = None,
    **filters
) -> tuple[list[T], dict]
exists(**filters) -> bool
count(**filters) -> int

# Update
update(id, data: dict, commit: bool = True) -> T | None
update_many(filters: dict, data: dict, commit: bool = True) -> int

# Delete
delete(id, commit: bool = True, force: bool = False) -> bool
delete_many(filters: dict, commit: bool = True) -> int

# Utility
refresh(instance: T) -> T
commit() -> None
rollback() -> None
flush() -> None
```

**`_order_by` accepts:**
- `str` — single field, optionally prefixed with `-` for DESC (e.g. `'-created_at'`)
- `list[str]` — multiple fields applied in order (e.g. `['-priority', 'due_date', 'name']`)
- `None` — no ordering applied

### DatabaseManager / AsyncDatabaseManager

```
__init__(config, connection_name='default', read_replicas=None, echo=False)

get_session() -> Session | AsyncSession
get_read_session() -> Session | AsyncSession

session() -> contextmanager / asynccontextmanager
read_session() -> contextmanager / asynccontextmanager

health_check() -> dict[str, bool]
dispose() -> None          # async: await dispose()
```

### TranslatableMixin

```
set_locale(locale: str) -> self
get_locale() -> str

set_global_locale(locale: str) -> None          # classmethod
get_global_locale() -> str                       # classmethod

set_translation(field, value, locale=None) -> self
get_translation(field, locale=None, fallback=True) -> str | None
get_translations(field) -> dict[str, str]
has_translation(field, locale=None) -> bool
validate_translations(required_locales=None) -> dict[str, list[str]]
```

---

## Next Steps

- **[Services](/docs/services)** - Build on repository pattern with lifecycle hooks
- **[Validation](/docs/validation)** - Validate data before saving
