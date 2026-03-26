# Services

- [Introduction](#introduction)
- [Quick Start](#quick-start)
- [BaseCrudService](#basecrudservice)
- [AsyncBaseCrudService](#asyncbasecrudservice)
- [Response Schema Mapping](#response-schema-mapping)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Validation Hooks](#validation-hooks)
- [CRUD Operations](#crud-operations)
- [SlugServiceMixin](#slugservicemixin)
- [Advanced Patterns](#advanced-patterns)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's service layer provides a business logic layer on top of the repository pattern. Services handle validation, lifecycle hooks, transactions, and complex business rules, keeping your code organized and maintainable.

**Key Features:**

- **Business Logic Layer** - Separate concerns from database operations
- **Lifecycle Hooks** - Execute code before/after operations (sync & async)
- **Validation Hooks** - Custom validation logic (sync & async)
- **Transaction Control** - Commit control for complex operations
- **Response Mapping** - Automatic Pydantic schema conversion
- **Multi-Field Ordering** - Order results by multiple fields with per-field direction
- **Type-safe** - Full generic type support with 4 type parameters
- **Repository Integration** - Built on repository pattern
- **Async Support** - Full async/await support with `AsyncBaseCrudService`
- **Mixins** - `SlugServiceMixin` for automatic slug generation

---

<a name="quick-start"></a>
## Quick Start

### Sync Service

```python
from fastkit_core.services import BaseCrudService
from fastkit_core.database import Repository
from models import User
from schemas import UserCreate, UserUpdate, UserResponse

class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):

    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=UserResponse)

    def validate_create(self, data: UserCreate) -> None:
        if self.exists(email=data.email):
            raise ValueError("Email already exists")

    def before_create(self, data: dict) -> dict:
        data['password'] = hash_password(data['password'])
        return data

    def after_create(self, instance: User) -> None:
        send_welcome_email(instance.email)
```

### Async Service

```python
from fastkit_core.services import AsyncBaseCrudService
from fastkit_core.database import AsyncRepository

class UserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):

    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=UserResponse)

    async def validate_create(self, data: UserCreate) -> None:
        if await self.exists(email=data.email):
            raise ValueError("Email already exists")

    async def before_create(self, data: dict) -> dict:
        data['password'] = await hash_password_async(data['password'])
        return data

    async def after_create(self, instance: User) -> None:
        await send_welcome_email_async(instance.email)
```

### Use in FastAPI

```python
from fastapi import FastAPI, Depends
from fastkit_core.database import init_database, get_db, Repository
from fastkit_core.http import success_response
from fastkit_core.config import ConfigManager
from sqlalchemy.orm import Session

config = ConfigManager()
init_database(config)
app = FastAPI()

def get_user_service(session: Session = Depends(get_db)) -> UserService:
    return UserService(Repository(User, session))

@app.post("/users")
def create_user(user_data: UserCreate, service: UserService = Depends(get_user_service)):
    user_response = service.create(user_data)
    return success_response(data=user_response.model_dump(), status_code=201)

@app.get("/users")
def list_users(page: int = 1, per_page: int = 20, service: UserService = Depends(get_user_service)):
    users, meta = service.paginate(page=page, per_page=per_page)
    return {'items': [u.model_dump() for u in users], 'pagination': meta}
```

---

<a name="basecrudservice"></a>
## BaseCrudService

`BaseCrudService` is a generic base class providing CRUD operations with hooks for synchronous operations.

### Type Parameters

```python
class MyService(BaseCrudService[
    ModelType,          # SQLAlchemy model — e.g. User
    CreateSchemaType,   # Pydantic schema for creation — e.g. UserCreate
    UpdateSchemaType,   # Pydantic schema for updates — e.g. UserUpdate
    ResponseSchemaType  # Pydantic schema for responses — e.g. UserResponse
]):
    pass
```

### Setup

```python
from fastkit_core.services import BaseCrudService
from fastkit_core.database import Repository

# With response mapping — all methods return ProductResponse
class ProductService(BaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=ProductResponse)

# Without response mapping — all methods return the model directly
class ProductService(BaseCrudService[Product, ProductCreate, ProductUpdate, Product]):
    def __init__(self, repository: Repository):
        super().__init__(repository)
```

---

<a name="asyncbasecrudservice"></a>
## AsyncBaseCrudService

`AsyncBaseCrudService` provides full async/await support with the same API as `BaseCrudService`. All CRUD methods are coroutines.

```python
from fastkit_core.services import AsyncBaseCrudService
from fastkit_core.database import AsyncRepository

class ProductService(AsyncBaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):
    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=ProductResponse)

# All operations are async
product = await service.create(ProductCreate(name="Widget", price=9.99))
product = await service.find(1)
products = await service.get_all()
products, meta = await service.paginate(page=1, per_page=20)
updated = await service.update(1, ProductUpdate(price=12.99))
deleted = await service.delete(1)
```

### Use in FastAPI

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastkit_core.database import get_async_db, AsyncRepository

async def get_product_service(session: AsyncSession = Depends(get_async_db)) -> ProductService:
    return ProductService(AsyncRepository(Product, session))

@app.post("/products")
async def create_product(product_data: ProductCreate, service: ProductService = Depends(get_product_service)):
    result = await service.create(product_data)
    return success_response(data=result.model_dump())
```

---

<a name="response-schema-mapping"></a>
## Response Schema Mapping

When a `response_schema` is provided, all service methods automatically convert model instances to that schema before returning.

```python
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    # password excluded!

    model_config = {'from_attributes': True}

class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=UserResponse)

# Every method returns UserResponse, never the raw User model
user: UserResponse = service.create(user_data)
user: UserResponse = service.find(1)
users: list[UserResponse] = service.get_all()
users: list[UserResponse] = service.filter(status='active')
users, meta = service.paginate(page=1, per_page=20)
```

Without `response_schema`, all methods return the SQLAlchemy model instance directly.

---

<a name="lifecycle-hooks"></a>
## Lifecycle Hooks

Lifecycle hooks let you execute code before and after each operation. Override only the hooks you need.

### Sync Hooks

```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):

    def before_create(self, data: dict) -> dict:
        data['password'] = hash_password(data['password'])
        return data  # Must return data

    def after_create(self, instance: User) -> None:
        send_welcome_email(instance.email)
        create_user_profile(instance.id)

    def before_update(self, id: int, data: dict) -> dict:
        data['updated_by'] = get_current_user_id()
        return data

    def after_update(self, instance: User) -> None:
        cache.delete(f'user:{instance.id}')

    def before_delete(self, id: int) -> None:
        user = self.find_or_fail(id)
        if user.has_active_subscriptions():
            raise ValueError("Cannot delete user with active subscriptions")

    def after_delete(self, id: int) -> None:
        delete_user_files(id)
        revoke_user_tokens(id)
```

### Async Hooks

```python
class UserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):

    async def before_create(self, data: dict) -> dict:
        data['password'] = await hash_password_async(data['password'])
        return data

    async def after_create(self, instance: User) -> None:
        await send_welcome_email_async(instance.email)

    async def before_update(self, id: int, data: dict) -> dict:
        data['updated_by'] = await get_current_user_id_async()
        return data

    async def after_update(self, instance: User) -> None:
        await cache.delete_async(f'user:{instance.id}')

    async def before_delete(self, id: int) -> None:
        user = await self.find_or_fail(id)
        if await user.has_active_subscriptions_async():
            raise ValueError("Cannot delete user with active subscriptions")

    async def after_delete(self, id: int) -> None:
        await delete_user_files_async(id)
```

### Hook Execution Order

```
validate_create → before_create → [repository.create] → after_create
validate_update → before_update → [repository.update] → after_update
                  before_delete → [repository.delete] → after_delete
```

---

<a name="validation-hooks"></a>
## Validation Hooks

Validation hooks run before the lifecycle hooks and are the correct place for business rule validation.

### Sync

```python
class ProductService(BaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):

    def validate_create(self, data: ProductCreate) -> None:
        if self.exists(sku=data.sku):
            raise ValueError("SKU already exists")

        if data.price < 0:
            raise ValueError("Price must be positive")

    def validate_update(self, id: int, data: ProductUpdate) -> None:
        product = self.find_or_fail(id)

        if data.price and data.price < product.cost:
            raise ValueError("Price cannot be lower than cost")
```

### Async

```python
class ProductService(AsyncBaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):

    async def validate_create(self, data: ProductCreate) -> None:
        if await self.exists(sku=data.sku):
            raise ValueError("SKU already exists")

        if not await external_inventory_check(data.sku):
            raise ValueError("SKU not found in inventory system")

    async def validate_update(self, id: int, data: ProductUpdate) -> None:
        product = await self.find_or_fail(id)

        if data.price and data.price < product.cost:
            raise ValueError("Price cannot be lower than cost")
```

---

<a name="crud-operations"></a>
## CRUD Operations

### Read Operations

```python
# Sync
product = service.find(1)                    # None if not found
product = service.find_or_fail(1)            # ValueError if not found
products = service.get_all()
products = service.get_all(limit=100)
products = service.filter(status='active')
product = service.filter_one(sku='ABC123')   # First matching record
exists = service.exists(sku='ABC123')
count = service.count(status='active')

# Async — same API with await
product = await service.find(1)
products = await service.get_all()
product = await service.filter_one(sku='ABC123')
```

### Ordering

`_order_by` accepts a single string or a list of strings. Prefix with `-` for descending order.

```python
# Single field
products = service.filter(status='active', _order_by='-created_at')

# Multiple fields — list syntax
# ORDER BY department ASC, score DESC
users = service.filter(_order_by=['department', '-score'])

# Three fields
tasks = service.filter(_order_by=['-priority', 'due_date', 'name'])

# Works on all read methods
users = service.get_all(_order_by=['-created_at', 'name'])
user = service.filter_one(_order_by='-score', status='active')
users, meta = service.paginate(page=1, per_page=20, _order_by=['-created_at', 'name'])

# Async — identical API
users = await service.filter(_order_by=['-priority', 'name'])
users = await service.get_all(_order_by='name')
users, meta = await service.paginate(page=1, _order_by=['-created_at', 'name'])
```

### Filter with Operators

```python
# Sync
adults = service.filter(age__gte=18, status='active')
cheap = service.filter(price__lt=100, stock__gt=0)
gmail = service.filter(email__ilike='%@gmail.com')
products = service.filter(
    status='active',
    price__gte=10,
    _limit=20,
    _offset=40,
    _order_by='-created_at'
)

# Async
adults = await service.filter(age__gte=18, status='active')
```

### Pagination

```python
# Sync
products, meta = service.paginate(page=1, per_page=20)
products, meta = service.paginate(
    page=2,
    per_page=20,
    status='active',
    price__gte=10,
    _order_by=['-created_at', 'name']
)

print(meta)
# {'page': 2, 'per_page': 20, 'total': 150, 'total_pages': 8, 'has_next': True, 'has_prev': True}

# Async
products, meta = await service.paginate(page=1, per_page=20)
```

### Eager Loading

Services pass `load_relations` and `_load_relations` directly to the repository. All N+1 prevention happens at the repository level.

```python
from sqlalchemy.orm import selectinload

# Sync
user = service.find(1, load_relations=[selectinload(User.posts)])
user = service.find_or_fail(1, load_relations=[selectinload(User.posts)])
users = service.get_all(load_relations=[selectinload(User.posts)])
users = service.filter(status='active', _load_relations=[selectinload(User.posts)])
user = service.filter_one(email='john@test.com', load_relations=[selectinload(User.posts)])
users, meta = service.paginate(page=1, per_page=20, _load_relations=[selectinload(User.posts)])

# Async — same API with await
user = await service.find(1, load_relations=[selectinload(User.posts)])
users = await service.filter(status='active', _load_relations=[selectinload(User.posts)])
users, meta = await service.paginate(page=1, _load_relations=[selectinload(User.posts)])
```

Eager loading is compatible with response schema mapping — relationships are loaded before the model is converted to the response schema.

### Create Operations

```python
# Sync
product = service.create(ProductCreate(name="Widget", price=9.99))
products = service.create_many([ProductCreate(name="A"), ProductCreate(name="B")])
product = service.create(data, commit=False)
service.commit()

# Async
product = await service.create(ProductCreate(name="Widget", price=9.99))
products = await service.create_many([...])
```

### Update Operations

```python
# Sync
product = service.update(1, ProductUpdate(price=12.99))
count = service.update_many(filters={'status': 'pending'}, data=ProductUpdate(status='active'))

# Async
product = await service.update(1, ProductUpdate(price=12.99))
count = await service.update_many(filters={'status': 'pending'}, data=ProductUpdate(status='active'))
```

### Delete Operations

```python
# Sync
deleted = service.delete(1)                          # Soft delete if supported
deleted = service.delete(1, force=True)              # Force hard delete
count = service.delete_many({'status': 'inactive'})

# Async
deleted = await service.delete(1)
count = await service.delete_many({'status': 'inactive'})
```

### Transaction Control

```python
# Sync
try:
    user = service.create(user_data, commit=False)
    profile = profile_service.create(profile_data, commit=False)
    service.commit()
except Exception:
    service.rollback()
    raise

# Async
try:
    user = await service.create(user_data, commit=False)
    profile = await profile_service.create(profile_data, commit=False)
    await service.commit()
except Exception:
    await service.rollback()
    raise
```

---

<a name="slugservicemixin"></a>
## SlugServiceMixin

Automatic slug generation with uniqueness checking.

### Setup

```python
from fastkit_core.services import BaseCrudService, SlugServiceMixin

# Sync
class ArticleService(SlugServiceMixin, BaseCrudService[Article, ArticleCreate, ArticleUpdate, ArticleResponse]):

    def before_create(self, data: dict) -> dict:
        data['slug'] = self.generate_slug(data['title'])
        return data

    def before_update(self, id: int, data: dict) -> dict:
        if 'title' in data:
            data['slug'] = self.generate_slug(data['title'], exclude_id=id)
        return data

# Async
class ArticleService(SlugServiceMixin, AsyncBaseCrudService[Article, ArticleCreate, ArticleUpdate, ArticleResponse]):

    async def before_create(self, data: dict) -> dict:
        data['slug'] = await self.async_generate_slug(data['title'])
        return data

    async def before_update(self, id: int, data: dict) -> dict:
        if 'title' in data:
            data['slug'] = await self.async_generate_slug(data['title'], exclude_id=id)
        return data
```

### Features

```python
# Static slugification — no database check
slug = SlugServiceMixin.slugify("Hello World!")    # "hello-world"
slug = SlugServiceMixin.slugify("Café au Lait")    # "cafe-au-lait"

# With uniqueness check — appends number if already taken
slug = service.generate_slug("Hello World")        # "hello-world"
slug = service.generate_slug("Hello World")        # "hello-world-2"

# Custom parameters
slug = service.generate_slug(
    text="My Article Title",
    slug_field='slug',      # Field name to check uniqueness against
    exclude_id=5,           # Exclude this ID (for updates)
    separator='_',          # Default: '-'
    max_length=100          # Default: 255
)
```

After 1000 duplicate attempts a random 8-character suffix is appended to prevent infinite loops.

---

<a name="advanced-patterns"></a>
## Advanced Patterns

### Custom Business Methods

```python
class OrderService(AsyncBaseCrudService[Order, OrderCreate, OrderUpdate, OrderResponse]):

    async def cancel_order(self, order_id: int, reason: str) -> OrderResponse:
        order = await self.find_or_fail(order_id)

        if order.status == 'shipped':
            raise ValueError("Cannot cancel shipped orders")

        return await self.update(order_id, OrderUpdate(
            status='cancelled',
            cancel_reason=reason,
            cancelled_at=datetime.now()
        ))

    async def get_user_orders(self, user_id: int) -> list[OrderResponse]:
        return await self.filter(user_id=user_id, _order_by='-created_at')
```

### Multiple Services Coordination

```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):

    def __init__(self, repository: Repository, profile_service: 'ProfileService'):
        super().__init__(repository, response_schema=UserResponse)
        self.profile_service = profile_service

    def after_create(self, instance: User) -> None:
        self.profile_service.create(ProfileCreate(
            user_id=instance.id,
            display_name=instance.name
        ))
```

### Complex Validation

```python
class ArticleService(BaseCrudService[Article, ArticleCreate, ArticleUpdate, ArticleResponse]):

    def validate_create(self, data: ArticleCreate) -> None:
        if self.exists(slug=data.slug):
            raise ValueError("Slug already exists")

        if not category_exists(data.category_id):
            raise ValueError("Category not found")

        if len(data.content) < 100:
            raise ValueError("Article content too short")
```

---

<a name="best-practices"></a>
## Best Practices

**Keep services focused** — one service per domain entity. `UserService` handles users, `OrderService` handles orders.

**Put validation in hooks** — `validate_create` and `validate_update` are the right place for business rules, not route handlers.

**Use response schemas** — pass `response_schema` to automatically exclude sensitive fields and ensure consistent API output.

**Put side effects in lifecycle hooks** — sending emails, clearing caches, and publishing events belong in `after_create` / `after_update`, not in controllers.

**Use async properly** — avoid blocking calls inside async hooks. Use `await` and async versions of all I/O operations.

**Use dependency injection** — inject services via FastAPI `Depends()` rather than instantiating them in route handlers.

**Wrap multi-service writes in transactions** — use `commit=False` and manual `commit()` / `rollback()` when coordinating multiple services.

**Handle errors at the route layer** — let service hooks raise `ValueError` for business rule violations, and convert them to `HTTPException` in the route handler.

---

<a name="api-reference"></a>
## API Reference

### BaseCrudService / AsyncBaseCrudService

Both classes share an identical public interface. `AsyncBaseCrudService` methods are coroutines (use `await`).

**Validation Hooks:**
```
validate_create(data: CreateSchemaType) -> None
validate_update(id: Any, data: UpdateSchemaType) -> None
```

**Lifecycle Hooks:**
```
before_create(data: dict) -> dict
after_create(instance: ModelType) -> None
before_update(id: Any, data: dict) -> dict
after_update(instance: ModelType) -> None
before_delete(id: Any) -> None
after_delete(id: Any) -> None
```

**Read Operations:**
```
find(id, load_relations: Sequence[Load] | None = None) -> ResponseType | None
find_or_fail(id, load_relations: Sequence[Load] | None = None) -> ResponseType
get_all(
    limit: int | None = None,
    load_relations: Sequence[Load] | None = None,
    _order_by: str | list[str] | None = None
) -> list[ResponseType]
filter(
    _limit: int | None = None,
    _offset: int | None = None,
    _order_by: str | list[str] | None = None,
    _load_relations: Sequence[Load] | None = None,
    **filters
) -> list[ResponseType]
filter_one(
    load_relations: Sequence[Load] | None = None,
    _order_by: str | list[str] | None = None,
    **filters
) -> ResponseType | None
paginate(
    page: int = 1,
    per_page: int = 20,
    _order_by: str | list[str] | None = None,
    _load_relations: Sequence[Load] | None = None,
    **filters
) -> tuple[list[ResponseType], dict]
exists(**filters) -> bool
count(**filters) -> int
```

**`_order_by` accepts:**
- `str` — single field, optionally prefixed with `-` for DESC (e.g. `'-created_at'`)
- `list[str]` — multiple fields applied in order (e.g. `['-priority', 'due_date', 'name']`)
- `None` — no ordering applied

**Create Operations:**
```
create(data: CreateSchemaType, commit: bool = True) -> ResponseType
create_many(data_list: list[CreateSchemaType], commit: bool = True) -> list[ResponseType]
```

**Update Operations:**
```
update(id, data: UpdateSchemaType, commit: bool = True) -> ResponseType | None
update_many(filters: dict, data: UpdateSchemaType, commit: bool = True) -> int
```

**Delete Operations:**
```
delete(id, commit: bool = True, force: bool = False) -> bool
delete_many(filters: dict, commit: bool = True) -> int
```

**Transaction Management:**
```
commit() -> None
rollback() -> None
flush() -> None
```

### SlugServiceMixin

```
slugify(text: str, separator: str = '-', max_length: int = 255) -> str   # staticmethod

generate_slug(
    text: str,
    slug_field: str = 'slug',
    exclude_id: Any | None = None,
    separator: str = '-',
    max_length: int = 255
) -> str

async_generate_slug(
    text: str,
    slug_field: str = 'slug',
    exclude_id: Any | None = None,
    separator: str = '-',
    max_length: int = 255
) -> str                  # coroutine
```

---

## Complete Example

```python
# models.py
from fastkit_core.database import Base, IntIdMixin, TimestampMixin, SlugMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text

class Article(Base, IntIdMixin, TimestampMixin, SlugMixin):
    __tablename__ = 'articles'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int]
    category_id: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default='draft')
```

```python
# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime

class ArticleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=100)
    author_id: int
    category_id: int

class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category_id: int | None = None
    status: str | None = None

class ArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    author_id: int
    category_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
```

```python
# services.py
from fastkit_core.services import AsyncBaseCrudService, SlugServiceMixin
from fastkit_core.database import AsyncRepository

class ArticleService(SlugServiceMixin, AsyncBaseCrudService[
    Article, ArticleCreate, ArticleUpdate, ArticleResponse
]):
    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=ArticleResponse)

    async def validate_create(self, data: ArticleCreate) -> None:
        if not await author_exists(data.author_id):
            raise ValueError("Author not found")
        if not await category_exists(data.category_id):
            raise ValueError("Category not found")

    async def before_create(self, data: dict) -> dict:
        data['slug'] = await self.async_generate_slug(data['title'])
        return data

    async def before_update(self, id: int, data: dict) -> dict:
        if 'title' in data:
            data['slug'] = await self.async_generate_slug(data['title'], exclude_id=id)
        return data

    async def after_create(self, instance: Article) -> None:
        await search_index.add_article_async(instance)

    async def after_update(self, instance: Article) -> None:
        await cache.delete_async(f'article:{instance.id}')
        await search_index.update_article_async(instance)

    async def publish(self, article_id: int) -> ArticleResponse:
        article = await self.find_or_fail(article_id)
        if article.status == 'published':
            raise ValueError("Article already published")
        return await self.update(article_id, ArticleUpdate(status='published'))
```

```python
# main.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastkit_core.database import init_async_database, get_async_db, AsyncRepository
from fastkit_core.http import success_response, paginated_response
from fastkit_core.config import ConfigManager

config = ConfigManager()
init_async_database(config)
app = FastAPI()

async def get_article_service(session: AsyncSession = Depends(get_async_db)) -> ArticleService:
    return ArticleService(AsyncRepository(Article, session))

@app.post("/articles", status_code=201)
async def create_article(article: ArticleCreate, service: ArticleService = Depends(get_article_service)):
    result = await service.create(article)
    return success_response(data=result.model_dump(), status_code=201)

@app.get("/articles")
async def list_articles(
    page: int = 1,
    per_page: int = 20,
    status: str = 'published',
    service: ArticleService = Depends(get_article_service)
):
    articles, meta = await service.paginate(
        page=page,
        per_page=per_page,
        status=status,
        _order_by='-created_at'
    )
    return paginated_response(items=[a.model_dump() for a in articles], pagination=meta)

@app.get("/articles/{article_id}")
async def get_article(article_id: int, service: ArticleService = Depends(get_article_service)):
    article = await service.find_or_fail(article_id)
    return success_response(data=article.model_dump())

@app.put("/articles/{article_id}")
async def update_article(
    article_id: int,
    article: ArticleUpdate,
    service: ArticleService = Depends(get_article_service)
):
    updated = await service.update(article_id, article)
    return success_response(data=updated.model_dump())

@app.post("/articles/{article_id}/publish")
async def publish_article(article_id: int, service: ArticleService = Depends(get_article_service)):
    published = await service.publish(article_id)
    return success_response(data=published.model_dump())

@app.delete("/articles/{article_id}", status_code=204)
async def delete_article(article_id: int, service: ArticleService = Depends(get_article_service)):
    await service.delete(article_id)
```

---

## Next Steps

- **[Database](database.md)** - Repository pattern and model configuration
- **[Validation](validation.md)** - Schema validation with Pydantic
- **[HTTP](http_utilities.md)** - Response formatting helpers
