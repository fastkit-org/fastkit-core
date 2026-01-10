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
pip install fastkit-core[postgresql]

# With MySQL async support
pip install fastkit-core[mysql]
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

# Automatically has:
# id: Mapped[UUID] - UUID v4 primary key

user = User(name="Alice")
print(user.id)  # UUID('550e8400-e29b-41d4-a716-446655440000')
```

**When to use:**
- Distributed systems
- Public-facing IDs (non-sequential)
- Security (harder to guess)
- Merging databases

### TimestampMixin

Automatic created_at and updated_at timestamps:

```python
from fastkit_core.database import Base, IntIdMixin, TimestampMixin

class Post(Base, IntIdMixin, TimestampMixin):
    title: Mapped[str]

# Automatically has:
# created_at: Mapped[datetime] - set on creation
# updated_at: Mapped[datetime] - updated automatically

post = Post(title="Hello")
session.add(post)
session.commit()

print(post.created_at)  # 2025-01-10 10:30:00
print(post.updated_at)  # 2025-01-10 10:30:00

# Update
post.title = "Hello World"
session.commit()

print(post.updated_at)  # 2025-01-10 10:35:00 (auto-updated!)
```

### SoftDeleteMixin

Soft delete support (mark as deleted instead of removing):

```python
from fastkit_core.database import Base, IntIdMixin, SoftDeleteMixin

class Post(Base, IntIdMixin, SoftDeleteMixin):
    title: Mapped[str]

# Automatically has:
# deleted_at: Mapped[datetime | None] - null = active

# Soft delete
post.soft_delete()
print(post.is_deleted)  # True
print(post.deleted_at)  # 2025-01-10 10:40:00

# Restore
post.restore()
print(post.is_deleted)  # False
print(post.deleted_at)  # None

# Query helpers
active_posts = Post.active(session).all()      # Only non-deleted
deleted_posts = Post.deleted(session).all()    # Only deleted
all_posts = Post.with_deleted(session).all()   # Including deleted
```

### SlugMixin

Automatic URL-friendly slug, generating slug you can do by `SlugServiceMixin`

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

# Automatically has:
# published_at: Mapped[datetime | None]

article = Article(title="News")

# States
print(article.is_draft)       # True
print(article.is_published)   # False
print(article.is_scheduled)   # False

# Publish immediately
article.publish()
print(article.is_published)   # True

# Unpublish (make draft)
article.unpublish()
print(article.is_draft)       # True

# Schedule for future
future = datetime.now(timezone.utc) + timedelta(days=7)
article.schedule(future)
print(article.is_scheduled)   # True

# Query helpers
published = Article.published(session).all()   # Published articles
drafts = Article.drafts(session).all()         # Draft articles
scheduled = Article.scheduled(session).all()   # Scheduled articles
```

---

<a name="session-management"></a>
## Session Management

### Configuration

Database connections are configured in your config file:

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
    
    # Read replica
    'read_replica_1': {
        'driver': 'postgresql',
        'host': 'replica1.example.com',
        'port': 5432,
        'database': 'myapp',
        'username': 'readonly',
        'password': 'secret',
    },
    
    # Or use direct URL
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
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastkit_core.database import init_database, shutdown_database
from fastkit_core.config import ConfigManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = ConfigManager()
    
    # Simple initialization
    init_database(config)
    
    # With read replicas
    init_database(
        config,
        connection_name='default',
        read_replicas=['read_replica_1', 'read_replica_2']
    )
    
    # With SQL echo (debugging)
    init_database(config, echo=True)
    
    yield
    
    # Shutdown
    shutdown_database()

app = FastAPI(lifespan=lifespan)
```

### Using Sessions

**Context manager (recommended):**
```python
from fastkit_core.database import get_db_manager

db = get_db_manager()

# Write operation
with db.session() as session:
    user = User(name="John")
    session.add(user)
    # Auto-commits on success, rolls back on error

# Read operation (uses read replicas if configured)
with db.read_session() as session:
    users = session.query(User).all()
```

**FastAPI dependency injection:**
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from fastkit_core.database import get_db, get_read_db

# Write endpoint
@app.post("/users")
def create_user(data: dict, session: Session = Depends(get_db)):
    user = User(**data)
    session.add(user)
    session.commit()
    return user.to_dict()

# Read endpoint (uses replicas)
@app.get("/users")
def list_users(session: Session = Depends(get_read_db)):
    return session.query(User).all()
```

### Health Checks

```python
from fastkit_core.database import health_check_all

# Check all connections
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
    users = repo.get_all(limit=100)
    return [user.to_dict() for user in users]
```

### CRUD Operations

**Create:**
```python
# Single record
user = repo.create({
    'name': 'John Doe',
    'email': 'john@example.com'
})

# Multiple records
users = repo.create_many([
    {'name': 'John', 'email': 'john@test.com'},
    {'name': 'Jane', 'email': 'jane@test.com'}
])

# Without auto-commit
user = repo.create({'name': 'John'}, commit=False)
repo.commit()  # Manual commit
```

**Read:**
```python
# By ID
user = repo.get(1)

# Or raise exception if not found
user = repo.get_or_404(1)

# All records
users = repo.get_all()
users = repo.get_all(limit=100)

# First matching
user = repo.first(email='john@test.com')

# Check existence
exists = repo.exists(email='john@test.com')

# Count
total = repo.count()
active_count = repo.count(status='active')
```

**Update:**
```python
# Single record
user = repo.update(1, {'name': 'Jane Doe'})

# Multiple records
count = repo.update_many(
    filters={'status': 'pending'},
    data={'status': 'active'}
)
```

**Delete:**
```python
# Single record (soft delete if supported)
deleted = repo.delete(1)

# Force hard delete
deleted = repo.delete(1, force=True)

# Multiple records
count = repo.delete_many({'status': 'inactive'})
```

### Filtering

Django-style filtering with operator support:

```python
# Simple equality
users = repo.filter(status='active')

# Greater than / less than
adults = repo.filter(age__gte=18, age__lt=65)

# Pattern matching
gmail_users = repo.filter(email__ilike='%@gmail.com')
names_starting_with_j = repo.filter(name__startswith='J')
names_containing_doe = repo.filter(name__contains='doe')

# IN lists
active_users = repo.filter(status__in=['active', 'pending'])

# NULL checks
users_without_email = repo.filter(email__is_null=True)
users_with_email = repo.filter(email__is_not_null=True)

# BETWEEN
products = repo.filter(price__between=(10, 100))

# With limit, offset, ordering
users = repo.filter(
    status='active',
    age__gte=18,
    _limit=10,
    _offset=20,
    _order_by='-created_at'  # DESC
)
```

**Available operators:**
- `eq` - Equal (default if no operator)
- `ne` - Not equal
- `lt`, `lte`, `gt`, `gte` - Comparisons
- `in`, `not_in` - IN/NOT IN lists
- `like`, `ilike` - LIKE patterns (ilike is case-insensitive)
- `is_null` - IS NULL (pass True/False)
- `is_not_null` - IS NOT NULL
- `between` - BETWEEN (pass tuple/list of 2 values)
- `startswith`, `endswith`, `contains` - String patterns

### Pagination

```python
# Simple pagination
users, meta = repo.paginate(page=1, per_page=20)

# With filters and ordering
users, meta = repo.paginate(
    page=2,
    per_page=20,
    _order_by='-created_at',
    status='active',
    age__gte=18
)

# Metadata structure
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

### Transaction Management

```python
# Manual transaction control
try:
    user = repo.create({'name': 'John'}, commit=False)
    profile = profile_repo.create({'user_id': user.id}, commit=False)
    
    repo.commit()  # Commit both or neither
except Exception:
    repo.rollback()
    raise

# Or use flush for intermediate operations
repo.create({'name': 'John'}, commit=False)
repo.flush()  # Send to DB but don't commit
print(user.id)  # ID is available after flush
```

---

<a name="async-support"></a>
## Async Support

FastKit Core provides full async support with feature parity to sync operations.

### Async Session Management

**Initialize:**
```python
from fastkit_core.database import init_async_database
from fastkit_core.config import ConfigManager
configuration = ConfigManager(modules=['database'])
init_async_database(configuration)
```

**FastAPI async dependency:**
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastkit_core.database import get_async_db, get_async_read_db

@app.post("/users")
async def create_user(
    data: dict,
    session: AsyncSession = Depends(get_async_db)
):
    user = User(**data)
    session.add(user)
    await session.commit()
    return user.to_dict()

@app.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_async_read_db)
):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [user.to_dict() for user in users]
```

### Async Repository

Full CRUD operations with async/await:

```python
from fastkit_core.database import AsyncRepository

repo = AsyncRepository(User, session)

# Create
user = await repo.create({'name': 'John', 'email': 'john@test.com'})
users = await repo.create_many([...])

# Read
user = await repo.get(1)
user = await repo.get_or_404(1)
users = await repo.get_all(limit=100)
user = await repo.first(email='john@test.com')
exists = await repo.exists(email='john@test.com')
count = await repo.count(status='active')

# Filter
users = await repo.filter(
    status='active',
    age__gte=18,
    _limit=10,
    _order_by='-created_at'
)

# Paginate
users, meta = await repo.paginate(
    page=1,
    per_page=20,
    status='active'
)

# Update
user = await repo.update(1, {'name': 'Jane'})
count = await repo.update_many({'status': 'pending'}, {'status': 'active'})

# Delete
deleted = await repo.delete(1)
count = await repo.delete_many({'status': 'inactive'})

```

**FastAPI with async repository:**
```python
from fastkit_core.database import AsyncRepository, get_async_db
from fastapi import Depends

async def get_user_repo(
    session: AsyncSession = Depends(get_async_db)
) -> AsyncRepository:
    return AsyncRepository(User, session)

@app.get("/users")
async def list_users(repo: AsyncRepository = Depends(get_user_repo)):
    users = await repo.get_all(limit=100)
    return [user.to_dict() for user in users]

@app.get("/users/{user_id}")
async def get_user(user_id: int, repo: AsyncRepository = Depends(get_user_repo)):
    user = await repo.get_or_404(user_id)
    return user.to_dict()
```

### Async Health Checks

```python
from fastkit_core.database import health_check_all_async

# Inside an async function
health = await health_check_all_async()
```

**Note:** Async shutdown is handled automatically in the `lifespan` context manager shown above.

---

<a name="translatablemixin"></a>
## TranslatableMixin

Automatic multi-language support with zero boilerplate.

### Setup

```python
from fastkit_core.database import Base, IntIdMixin, TimestampMixin, TranslatableMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON

class Article(Base, IntIdMixin, TimestampMixin, TranslatableMixin):
    __tablename__ = 'articles'
    __translatable__ = ['title', 'content']
    __fallback_locale__ = 'en'  # Optional - defaults to config
    
    # Translatable fields - MUST be JSON columns
    title: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)
    
    # Regular fields work normally
    author: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default='draft')
```

### Basic Usage

**Transparent string interface:**
```python
# Create article
article = Article(author="John")

# Set title for current locale (defaults to 'en')
article.title = "Hello World"
article.content = "This is content"

# Switch locale and add translation
article.set_locale('es')
article.title = "Hola Mundo"
article.content = "Este es el contenido"

# Switch back
article.set_locale('en')
print(article.title)  # "Hello World"

# Save to database
session.add(article)
session.commit()
```

### Explicit Translation Management

```python
# Set translation for specific locale
article.set_translation('title', 'Bonjour le monde', locale='fr')
article.set_translation('title', 'Hallo Welt', locale='de')

# Get translation for specific locale
title_es = article.get_translation('title', locale='es')
# "Hola Mundo"

# Get translation with fallback
title_ja = article.get_translation('title', locale='ja', fallback=True)
# Falls back to 'en' if 'ja' doesn't exist

# Get all translations
translations = article.get_translations('title')
# {
#     'en': 'Hello World',
#     'es': 'Hola Mundo',
#     'fr': 'Bonjour le monde',
#     'de': 'Hallo Welt'
# }

# Check if translation exists
has_spanish = article.has_translation('title', 'es')  # True
has_japanese = article.has_translation('title', 'ja')  # False
```

### Global Locale

```python
# Set global locale (affects all instances)
TranslatableMixin.set_global_locale('es')

# Now all articles will use Spanish
article = Article.query.first()
print(article.title)  # Returns Spanish version

# Get current global locale
current = TranslatableMixin.get_global_locale()
```

### FastAPI Integration

**Middleware:**
```python
from fastkit_core.database import set_locale_from_request
from fastapi import Request

@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    # Get locale from header
    locale = request.headers.get('Accept-Language', 'en')[:2]
    set_locale_from_request(locale)
    
    response = await call_next(request)
    return response
```

**In endpoints:**
```python
@app.get("/articles/{article_id}")
def get_article(
    article_id: int,
    locale: str = 'en',
    session: Session = Depends(get_db)
):
    repo = Repository(Article, session)
    article = repo.get(article_id)
    
    # Return article in specific locale
    return article.to_dict(locale=locale)
```

### Validation

```python
# Validate required translations
missing = article.validate_translations(
    required_locales=['en', 'es', 'fr']
)

if missing:
    print(missing)
    # {'content': ['fr']}  # French content is missing
```

### Serialization

```python
# Default locale
data = article.to_dict()
# Uses current locale

# Specific locale
data = article.to_dict(locale='es')
# {
#     'id': 1,
#     'title': 'Hola Mundo',
#     'content': 'Este es el contenido',
#     'author': 'John',
#     ...
# }

# With relationships
data = article.to_dict(
    include_relationships=True,
    locale='es'
)
```

---

<a name="connection-manager"></a>
## Connection Manager

Centralized manager for multiple database connections.

### Setup

```python
from fastkit_core.database import ConnectionManager
from fastkit_core.config import ConfigManager

config = ConfigManager()
conn_manager = ConnectionManager(config)

# Add primary database with read replicas
conn_manager.add_connection(
    name='default',
    read_replicas=['read_replica_1', 'read_replica_2']
)

# Add analytics database
conn_manager.add_connection(
    name='analytics',
    echo=True  # Enable SQL logging for this connection
)

# Add reporting database
conn_manager.add_connection(name='reporting')
```

### Using Connections

```python
# Get database managers
primary_db = conn_manager.get('default')
analytics_db = conn_manager.get('analytics')

# Use different databases
with primary_db.session() as session:
    user = User(name="John")
    session.add(user)

with analytics_db.session() as session:
    event = Event(type="signup", user_id=user.id)
    session.add(event)
```

### Health Checks

```python
# Check all connections
health = conn_manager.health_check_all()
# {
#     'default': {
#         'primary': True,
#         'read_replica_1': True,
#         'read_replica_2': True
#     },
#     'analytics': {
#         'primary': True
#     },
#     'reporting': {
#         'primary': False
#     }
# }
```

### Management

```python
# List connections
connections = conn_manager.list_connections()
# ['default', 'analytics', 'reporting']

# Check if connection exists
if conn_manager.has_connection('cache'):
    cache_db = conn_manager.get('cache')

# Remove connection
conn_manager.remove_connection('reporting')

# Dispose all connections (shutdown)
conn_manager.dispose_all()
```

### Global Instance

```python
from fastkit_core.database import (
    get_connection_manager,
    set_connection_manager
)

# Get global instance (creates if doesn't exist)
conn_manager = get_connection_manager()

# Or set your own
my_manager = ConnectionManager(config)
set_connection_manager(my_manager)
```

---

<a name="advanced-features"></a>
## Advanced Features

### Multiple Primary Keys

```python
from sqlalchemy import Integer

class UserRole(Base):
    __tablename__ = 'user_roles'
    
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Repository still works with composite keys
    repo = Repository(UserRole, session)
    # Note: get() won't work with composite keys
    # Use filter() instead
    user_role = repo.first(user_id=1, role_id=2)
```

### Relationships

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base, IntIdMixin, TimestampMixin):
    username: Mapped[str]
    
    # One-to-many
    posts: Mapped[list["Post"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan"
    )

class Post(Base, IntIdMixin, TimestampMixin):
    title: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    
    # Many-to-one
    author: Mapped["User"] = relationship(back_populates="posts")

# Serialize with relationships
user = repo.get(1)
data = user.to_dict(include_relationships=True, max_depth=2)
# {
#     'id': 1,
#     'username': 'alice',
#     'posts': [
#         {'id': 1, 'title': 'Post 1', 'author_id': 1},
#         {'id': 2, 'title': 'Post 2', 'author_id': 1}
#     ]
# }
```

### Complex Queries

```python
# Get query builder
query = repo.query()

# Build complex query
from sqlalchemy import and_, or_

query = query.where(
    and_(
        User.age >= 18,
        or_(
            User.status == 'active',
            User.status == 'pending'
        )
    )
)

# Execute
result = session.execute(query)
users = result.scalars().all()
```

### Transactions

```python
from fastkit_core.database import get_db_manager

db = get_db_manager()

# Manual transaction
with db.session() as session:
    try:
        # Multiple operations
        user_repo = Repository(User, session)
        user = user_repo.create({'name': 'John'}, commit=False)
        
        account_repo = Repository(Account, session)
        account = account_repo.create(
            {'user_id': user.id, 'balance': 0},
            commit=False
        )
        
        # Commit all or none
        session.commit()
        
    except Exception:
        session.rollback()
        raise
```

### Custom Repository Methods

```python
from fastkit_core.database import Repository

class UserRepository(Repository):
    """Custom repository with domain-specific methods."""
    
    def get_active_users(self):
        return self.filter(status='active', deleted_at__is_null=True)
    
    def find_by_email(self, email: str):
        return self.first(email=email)
    
    def search_by_name(self, query: str):
        return self.filter(name__ilike=f'%{query}%')

# Usage
repo = UserRepository(User, session)
active_users = repo.get_active_users()
user = repo.find_by_email('john@test.com')
```

---

<a name="best-practices"></a>
## Best Practices

### 1. Use Mixins Appropriately

✅ **Good:**
```python
class User(Base, IntIdMixin, TimestampMixin):
    """User with ID and timestamps."""
    pass

class BlogPost(Base, IntIdMixin, TimestampMixin, SoftDeleteMixin, SlugMixin):
    """Blog post with full features."""
    pass

class LogEntry(Base, IntIdMixin):
    """Logs don't need timestamps or soft delete."""
    pass
```

❌ **Bad:**
```python
class LogEntry(Base, SoftDeleteMixin, PublishableMixin):
    """Logs don't need soft delete or publishing."""
    pass
```

### 2. Repository Pattern

✅ **Good:**
```python
# In service layer
class UserService:
    def __init__(self, repository: Repository):
        self.repo = repository
    
    def get_active_users(self):
        return self.repo.filter(status='active')
    
    def register_user(self, data: dict):
        # Business logic here
        user = self.repo.create(data)
        send_welcome_email(user)
        return user
```

❌ **Bad:**
```python
# In controller - mixing concerns
@app.get("/users")
def list_users(session: Session = Depends(get_db)):
    users = session.query(User).filter_by(status='active').all()
    return users
```

### 3. Use Dependency Injection

✅ **Good:**
```python
def get_user_repo(session: Session = Depends(get_db)) -> Repository:
    return Repository(User, session)

@app.get("/users")
def list_users(repo: Repository = Depends(get_user_repo)):
    return repo.get_all()
```

### 4. Serialize Carefully

✅ **Good:**
```python
user = repo.get(1)
return user.to_dict(exclude=['password', 'secret_token'])
```

❌ **Bad:**
```python
user = repo.get(1)
return user.to_dict()  # Exposes sensitive fields!
```

### 5. Handle Soft Deletes

✅ **Good:**
```python
# Repository automatically excludes soft-deleted
users = repo.get_all()

# Explicitly include if needed
all_users = repo.get_all_with_deleted()
```

### 6. Use Filters Over Raw SQL

✅ **Good:**
```python
adults = repo.filter(age__gte=18, status='active')
```

❌ **Bad:**
```python
adults = session.query(User).filter(
    User.age >= 18,
    User.status == 'active'
).all()
```

### 7. Use Read Replicas

✅ **Good:**
```python
# Write to primary
@app.post("/users")
def create_user(data: dict, session: Session = Depends(get_db)):
    repo = Repository(User, session)
    return repo.create(data)

# Read from replica
@app.get("/users")
def list_users(session: Session = Depends(get_read_db)):
    repo = Repository(User, session)
    return repo.get_all()
```

### 8. Use Async for I/O-Bound Operations

✅ **Good:**
```python
@app.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_async_read_db)
):
    repo = AsyncRepository(User, session)
    users = await repo.get_all()
    return [user.to_dict() for user in users]
```

### 9. Validate Input Data

✅ **Good:**
```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users")
def create_user(
    data: UserCreate,
    session: Session = Depends(get_db)
):
    repo = Repository(User, session)
    user = repo.create(data.dict())
    return user.to_dict()
```

### 10. Use Transactions for Related Operations

✅ **Good:**
```python
with db.session() as session:
    try:
        user_repo = Repository(User, session)
        account_repo = Repository(Account, session)
        
        user = user_repo.create({'name': 'John'}, commit=False)
        account = account_repo.create(
            {'user_id': user.id},
            commit=False
        )
        
        session.commit()  # Commit both or neither
    except Exception:
        session.rollback()
        raise
```

---

<a name="api-reference"></a>
## API Reference

### Base

```python
class Base(DeclarativeBase):
    """Base model with serialization."""
    
    def to_dict(
        exclude: list[str] | None = None,
        include_relationships: bool = False,
        max_depth: int = 1,
        locale: str | None = None
    ) -> dict
    
    def to_json(
        exclude: list[str] | None = None,
        include_relationships: bool = False
    ) -> dict
    
    def update_from_dict(
        data: dict,
        exclude: list[str] | None = None,
        allow_only: list[str] | None = None
    ) -> None
    
    def __repr_attrs__(self) -> list[tuple[str, Any]]
```

### Repository

```python
class Repository(Generic[T]):
    def __init__(self, model: Type[T], session: Session)
    
    # Create
    def create(data: dict, commit: bool = True) -> T
    def create_many(data_list: list[dict], commit: bool = True) -> list[T]
    
    # Read
    def get(id: Any) -> T | None
    def get_or_404(id: Any) -> T
    def get_all(limit: int | None = None) -> list[T]
    def first(**filters) -> T | None
    def filter(_limit=None, _offset=None, _order_by=None, **filters) -> list[T]
    def paginate(page: int = 1, per_page: int = 20, **filters) -> tuple[list[T], dict]
    def exists(**filters) -> bool
    def count(**filters) -> int

    
    # Update
    def update(id: Any, data: dict, commit: bool = True) -> T | None
    def update_many(filters: dict, data: dict, commit: bool = True) -> int
    
    # Delete
    def delete(id: Any, commit: bool = True, force: bool = False) -> bool
    def delete_many(filters: dict, commit: bool = True) -> int
    
    # Utility
    def refresh(instance: T) -> T
    def commit() -> None
    def rollback() -> None
    def flush() -> None
```

### AsyncRepository

```python
class AsyncRepository(Generic[T]):
    """Same API as Repository but with async/await."""
    
    async def create(data: dict, commit: bool = True) -> T
    async def create_many(data_list: list[dict], commit: bool = True) -> list[T]
    
    async def get(id: Any) -> T | None
    async def get_or_404(id: Any) -> T
    async def get_all(limit: int | None = None) -> list[T]
    async def first(**filters) -> T | None
    async def filter(**filters) -> list[T]
    async def paginate(page: int, per_page: int, **filters) -> tuple[list[T], dict]
    async def exists(**filters) -> bool
    async def count(**filters) -> int
    
    async def update(id: Any, data: dict, commit: bool = True) -> T | None
    async def update_many(filters: dict, data: dict, commit: bool = True) -> int
    
    async def delete(id: Any, commit: bool = True, force: bool = False) -> bool
    async def delete_many(filters: dict, commit: bool = True) -> int
    
    async def refresh(instance: T) -> T
    async def commit() -> None
    async def rollback() -> None
    async def flush() -> None
```

### TranslatableMixin

```python
class TranslatableMixin:
    __translatable__: list[str]
    __fallback_locale__: str
    
    def set_locale(locale: str) -> self
    def get_locale() -> str
    
    @classmethod
    def set_global_locale(locale: str) -> None
    
    @classmethod
    def get_global_locale() -> str
    
    def set_translation(field: str, value: str, locale: str = None) -> self
    def get_translation(field: str, locale: str = None, fallback: bool = True) -> str | None
    def get_translations(field: str) -> dict[str, str]
    def has_translation(field: str, locale: str = None) -> bool
    def validate_translations(required_locales: list[str] = None) -> dict[str, list[str]]
```

### DatabaseManager

```python
class DatabaseManager:
    def __init__(
        config: ConfigManager,
        connection_name: str = 'default',
        read_replicas: list[str] | None = None,
        echo: bool = False
    )
    
    def get_session() -> Session
    def get_read_session() -> Session
    
    @contextmanager
    def session() -> Generator[Session, None, None]
    
    @contextmanager
    def read_session() -> Generator[Session, None, None]
    
    def health_check() -> dict[str, bool]
    def dispose() -> None
```

### AsyncDatabaseManager

```python
class AsyncDatabaseManager:
    def __init__(
        config: ConfigManager,
        connection_name: str = 'default',
        read_replicas: list[str] | None = None,
        echo: bool = False
    )
    
    def get_session() -> AsyncSession
    def get_read_session() -> AsyncSession
    
    @asynccontextmanager
    async def session() -> AsyncGenerator[AsyncSession, None]
    
    @asynccontextmanager
    async def read_session() -> AsyncGenerator[AsyncSession, None]
    
    async def health_check() -> dict[str, bool]
    async def dispose() -> None
```

### ConnectionManager

```python
class ConnectionManager:
    def __init__(config: ConfigManager, echo: bool = False)
    
    def add_connection(
        name: str,
        read_replicas: list[str] | None = None,
        echo: bool | None = None
    ) -> DatabaseManager
    
    def get(name: str = 'default') -> DatabaseManager
    def has_connection(name: str) -> bool
    def remove_connection(name: str) -> None
    def list_connections() -> list[str]
    def health_check_all() -> dict[str, dict[str, bool]]
    def dispose_all() -> None
```

---

## Complete Example

```python
# models.py
from fastkit_core.database import (
    Base,
    IntIdMixin,
    TimestampMixin,
    SoftDeleteMixin,
    TranslatableMixin
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, ForeignKey

class Article(
    Base,
    IntIdMixin,
    TimestampMixin,
    SoftDeleteMixin,
    TranslatableMixin
):
    __tablename__ = 'articles'
    __translatable__ = ['title', 'content']
    
    # Translatable fields (JSON)
    title: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)
    
    # Regular fields
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String(20), default='draft')
    
    # Relationships
    author: Mapped["User"] = relationship(back_populates="articles")

class User(Base, IntIdMixin, TimestampMixin):
    __tablename__ = 'users'
    
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    
    articles: Mapped[list["Article"]] = relationship(back_populates="author")
```

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastkit_core.database import (
    init_database,
    shutdown_database,
    get_db,
    Repository,
    set_locale_from_request
)
from fastkit_core.config import ConfigManager
from sqlalchemy.orm import Session
configuration = ConfigManager(modules=['database'])
init_database(configuration)

app = FastAPI(lifespan=lifespan)

# Locale middleware
@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    locale = request.headers.get('Accept-Language', 'en')[:2]
    set_locale_from_request(locale)
    response = await call_next(request)
    return response

# Dependencies
def get_article_repo(session: Session = Depends(get_db)) -> Repository:
    return Repository(Article, session)

# Routes
@app.post("/articles")
def create_article(data: dict, repo: Repository = Depends(get_article_repo)):
    article = repo.create(data)
    repo.commit()
    
    return article.to_dict()

@app.get("/articles")
def list_articles(
    page: int = 1,
    per_page: int = 20,
    repo: Repository = Depends(get_article_repo)
):
    articles, meta = repo.paginate(
        page=page,
        per_page=per_page,
        status='published'
    )
    
    return {
        'items': [a.to_dict() for a in articles],
        'pagination': meta
    }

@app.get("/articles/{article_id}")
def get_article(
    article_id: int,
    locale: str = 'en',
    repo: Repository = Depends(get_article_repo)
):
    article = repo.get_or_404(article_id)
    return article.to_dict(
        include_relationships=True,
        locale=locale
    )

@app.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, repo: Repository = Depends(get_article_repo)):
    repo.delete(article_id)  # Soft delete
```

---

## Next Steps

Now that you understand the database module:

- **[Services](/docs/services)** - Build on repository pattern
- **[Validation](/docs/validation)** - Validate data before saving