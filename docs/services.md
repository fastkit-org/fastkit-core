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
- **Type-safe** - Full generic type support with 4 type parameters
- **Reusable** - Extend for consistent patterns
- **Repository Integration** - Built on repository pattern
- **Async Support** - Full async/await support with AsyncBaseCrudService
- **Mixins** - SlugServiceMixin for automatic slug generation

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
    """User service with business logic."""
    
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=UserResponse)
    
    def validate_create(self, data: UserCreate) -> None:
        """Validate before creating user."""
        if self.exists(email=data.email):
            raise ValueError("Email already exists")
    
    def before_create(self, data: dict) -> dict:
        """Hash password before saving."""
        data['password'] = hash_password(data['password'])
        return data
    
    def after_create(self, instance: User) -> None:
        """Send welcome email after creation."""
        send_welcome_email(instance.email)
```

### Async Service

```python
from fastkit_core.services import AsyncBaseCrudService
from fastkit_core.database import AsyncRepository
from models import User
from schemas import UserCreate, UserUpdate, UserResponse

class UserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    """Async user service with business logic."""
    
    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=UserResponse)
    
    async def validate_create(self, data: UserCreate) -> None:
        """Validate before creating user."""
        if await self.exists(email=data.email):
            raise ValueError("Email already exists")
    
    async def before_create(self, data: dict) -> dict:
        """Hash password before saving."""
        data['password'] = await hash_password_async(data['password'])
        return data
    
    async def after_create(self, instance: User) -> None:
        """Send welcome email after creation."""
        await send_welcome_email_async(instance.email)
```

### Use in FastAPI

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastkit_core.database import init_database, shutdown_database, get_db
from fastkit_core.http import success_response
from sqlalchemy.orm import Session
from fastkit_core.config import ConfigManager
configuration = ConfigManager(modules=['database'])
init_database(configuration)

def get_user_service(session: Session = Depends(get_db)) -> UserService:
    repository = Repository(User, session)
    return UserService(repository)

@app.post("/users")
def create_user(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    # Service handles validation, hooks, and creation
    # Returns UserResponse thanks to response_schema
    user_response = service.create(user_data)
    
    return success_response(
        data=user_response.model_dump(),
        message="User created successfully",
        status_code=201
    )

@app.get("/users")
def list_users(
    page: int = 1,
    per_page: int = 20,
    service: UserService = Depends(get_user_service)
):
    users, meta = service.paginate(page=page, per_page=per_page)
    
    return {
        'items': [user.model_dump() for user in users],
        'pagination': meta
    }
```

---

<a name="basecrudservice"></a>
## BaseCrudService

`BaseCrudService` is a generic base class providing CRUD operations with hooks for synchronous operations.

### Type Parameters

```python
from fastkit_core.services import BaseCrudService

class MyService(BaseCrudService[
    ModelType,          # SQLAlchemy model
    CreateSchemaType,   # Pydantic schema for creation
    UpdateSchemaType,   # Pydantic schema for updates
    ResponseSchemaType  # Pydantic schema for responses (optional)
]):
    pass
```

**Type parameters:**
- `ModelType` - Your SQLAlchemy model (e.g., `User`)
- `CreateSchemaType` - Pydantic schema for creation (e.g., `UserCreate`)
- `UpdateSchemaType` - Pydantic schema for updates (e.g., `UserUpdate`)
- `ResponseSchemaType` - Pydantic schema for responses (e.g., `UserResponse`) - optional

### Basic Setup

```python
from fastkit_core.services import BaseCrudService
from fastkit_core.database import Repository
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse

# With response mapping
class ProductService(BaseCrudService[
    Product, 
    ProductCreate, 
    ProductUpdate,
    ProductResponse
]):
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=ProductResponse)

# Without response mapping (returns model directly)
class ProductService(BaseCrudService[
    Product, 
    ProductCreate, 
    ProductUpdate,
    Product  # Use model as response type
]):
    def __init__(self, repository: Repository):
        super().__init__(repository)  # No response_schema

# Usage
repository = Repository(Product, session)
service = ProductService(repository)

# Create - returns ProductResponse (if response_schema set)
product_response = service.create(ProductCreate(name="Widget", price=9.99))

# Read
product = service.find(1)
products = service.get_all()
products, meta = service.paginate(page=1, per_page=20)

# Update
updated = service.update(1, ProductUpdate(price=12.99))

# Delete
deleted = service.delete(1)
```

### Schema Conversion

Services automatically convert Pydantic models to dictionaries:

```python
# Pydantic v2
product_data = ProductCreate(name="Widget", price=9.99)
product = service.create(product_data)  # Auto-converts to dict

# Pydantic v1
product_data = ProductCreate(name="Widget", price=9.99)
product = service.create(product_data)  # Auto-converts using .dict()

# Dict input also works
product = service.create({"name": "Widget", "price": 9.99})

# Handles exclude_unset automatically
update_data = ProductUpdate(price=12.99)  # name not included
service.update(1, update_data)  # Only updates price
```

---

<a name="asyncbasecrudservice"></a>
## AsyncBaseCrudService

`AsyncBaseCrudService` provides full async/await support with the same API as `BaseCrudService`.

### Basic Setup

```python
from fastkit_core.services import AsyncBaseCrudService
from fastkit_core.database import AsyncRepository
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse

class ProductService(AsyncBaseCrudService[
    Product, 
    ProductCreate, 
    ProductUpdate,
    ProductResponse
]):
    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=ProductResponse)

# Usage
repository = AsyncRepository(Product, session)
service = ProductService(repository)

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

async def get_product_service(
    session: AsyncSession = Depends(get_async_db)
) -> ProductService:
    repository = AsyncRepository(Product, session)
    return ProductService(repository)

@app.post("/products")
async def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    product_response = await service.create(product_data)
    return success_response(data=product_response.model_dump())

@app.get("/products")
async def list_products(
    page: int = 1,
    per_page: int = 20,
    service: ProductService = Depends(get_product_service)
):
    products, meta = await service.paginate(page=page, per_page=per_page)
    return {
        'items': [p.model_dump() for p in products],
        'pagination': meta
    }
```

---

<a name="response-schema-mapping"></a>
## Response Schema Mapping

Services can automatically convert model instances to response schemas.

### With Response Mapping

```python
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    # password excluded!
    
    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True  # Pydantic v1

class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    def __init__(self, repository: Repository):
        # Pass response_schema to enable auto-mapping
        super().__init__(repository, response_schema=UserResponse)

# All methods return UserResponse instead of User model
user_response: UserResponse = service.create(user_data)
user_response: UserResponse = service.find(1)
users: list[UserResponse] = service.get_all()
```

### Without Response Mapping

```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, User]):
    def __init__(self, repository: Repository):
        # No response_schema - returns model directly
        super().__init__(repository)

# All methods return User model
user_model: User = service.create(user_data)
user_model: User = service.find(1)
users: list[User] = service.get_all()

# Manually convert if needed
user_dict = user_model.to_dict(exclude=['password'])
```

### Benefits of Response Mapping

1. **Security** - Exclude sensitive fields (passwords, tokens)
2. **Consistency** - Same response format across endpoints
3. **Validation** - Pydantic validates output
4. **Type Safety** - IDEs know exact return type
5. **Documentation** - OpenAPI docs show correct response schema

---

<a name="lifecycle-hooks"></a>
## Lifecycle Hooks

Lifecycle hooks let you execute code before and after operations.

### Sync Hooks

```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    def before_create(self, data: dict) -> dict:
        """Execute before creating a record."""
        data['password'] = hash_password(data['password'])
        data['created_by'] = get_current_user_id()
        return data
    
    def after_create(self, instance: User) -> None:
        """Execute after creating a record."""
        send_welcome_email(instance.email)
        create_user_profile(instance.id)
    
    def before_update(self, id: int, data: dict) -> dict:
        """Execute before updating a record."""
        data['updated_at'] = datetime.now()
        data['updated_by'] = get_current_user_id()
        return data
    
    def after_update(self, instance: User) -> None:
        """Execute after updating a record."""
        cache.delete(f'user:{instance.id}')
        notify_watchers(instance.id)
    
    def before_delete(self, id: int) -> None:
        """Execute before deleting a record."""
        user = self.find_or_fail(id)
        if user.has_active_subscriptions():
            raise ValueError("Cannot delete user with active subscriptions")
    
    def after_delete(self, id: int) -> None:
        """Execute after deleting a record."""
        delete_user_files(id)
        revoke_user_tokens(id)
```

### Async Hooks

```python
class UserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    async def before_create(self, data: dict) -> dict:
        """Execute before creating a record (async)."""
        data['password'] = await hash_password_async(data['password'])
        data['created_by'] = await get_current_user_id_async()
        return data
    
    async def after_create(self, instance: User) -> None:
        """Execute after creating a record (async)."""
        await send_welcome_email_async(instance.email)
        await create_user_profile_async(instance.id)
    
    async def before_update(self, id: int, data: dict) -> dict:
        """Execute before updating a record (async)."""
        data['updated_at'] = datetime.now()
        data['updated_by'] = await get_current_user_id_async()
        return data
    
    async def after_update(self, instance: User) -> None:
        """Execute after updating a record (async)."""
        await cache.delete_async(f'user:{instance.id}')
        await notify_watchers_async(instance.id)
    
    async def before_delete(self, id: int) -> None:
        """Execute before deleting a record (async)."""
        user = await self.find_or_fail(id)
        if await user.has_active_subscriptions_async():
            raise ValueError("Cannot delete user with active subscriptions")
    
    async def after_delete(self, id: int) -> None:
        """Execute after deleting a record (async)."""
        await delete_user_files_async(id)
        await revoke_user_tokens_async(id)
```

### Hook Use Cases

**before_create:**
- Hash passwords
- Set default values
- Add audit fields (created_by, created_at)
- Transform data
- Generate slugs or tokens

**after_create:**
- Send welcome emails
- Create related records
- Trigger events
- Update search indexes
- Log activities

**before_update:**
- Update timestamps
- Add audit fields (updated_by, updated_at)
- Validate ownership
- Transform data
- Generate new slugs if title changed

**after_update:**
- Clear caches
- Send notifications
- Update search indexes
- Trigger workflows
- Sync with external systems

**before_delete:**
- Validate deletion rules
- Check dependencies
- Archive data
- Prevent deletion based on business rules

**after_delete:**
- Delete related records
- Clean up files
- Revoke access tokens
- Log activities
- Update statistics

---

<a name="validation-hooks"></a>
## Validation Hooks

Validation hooks let you add custom business logic validation.

### Sync Validation

```python
class ProductService(BaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):
    
    def validate_create(self, data: ProductCreate) -> None:
        """Validate before creating product."""
        # Check uniqueness
        if self.exists(sku=data.sku):
            raise ValueError("SKU already exists")
        
        # Business rules
        if data.price < 0:
            raise ValueError("Price must be positive")
        
        if data.stock < 0:
            raise ValueError("Stock cannot be negative")
    
    def validate_update(self, id: int, data: ProductUpdate) -> None:
        """Validate before updating product."""
        product = self.find_or_fail(id)
        
        # Check ownership or permissions
        if not can_edit_product(product):
            raise ValueError("You don't have permission to edit this product")
        
        # Business rules
        if data.price and data.price < product.cost:
            raise ValueError("Price cannot be lower than cost")
```

### Async Validation

```python
class ProductService(AsyncBaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):
    
    async def validate_create(self, data: ProductCreate) -> None:
        """Validate before creating product (async)."""
        # Check uniqueness
        if await self.exists(sku=data.sku):
            raise ValueError("SKU already exists")
        
        # External validation
        if not await external_inventory_check(data.sku):
            raise ValueError("SKU not found in inventory system")
        
        # Business rules
        if data.price < 0:
            raise ValueError("Price must be positive")
    
    async def validate_update(self, id: int, data: ProductUpdate) -> None:
        """Validate before updating product (async)."""
        product = await self.find_or_fail(id)
        
        # Async permission check
        if not await can_edit_product_async(product):
            raise ValueError("You don't have permission to edit this product")
        
        # Business rules
        if data.price and data.price < product.cost:
            raise ValueError("Price cannot be lower than cost")
```

---

<a name="crud-operations"></a>
## CRUD Operations

### Read Operations

```python
# Sync
product = service.find(1)                    # Returns None if not found
product = service.find_or_fail(1)            # Raises ValueError if not found
products = service.get_all()                 # All records
products = service.get_all(limit=100)        # Limited
products = service.filter(status='active')   # Filter with operators
product = service.filter_one(sku='ABC123')   # First matching
exists = service.exists(sku='ABC123')        # Check existence
count = service.count(status='active')       # Count matching

# Async
product = await service.find(1)
product = await service.find_or_fail(1)
products = await service.get_all()
products = await service.get_all(limit=100)
products = await service.filter(status='active')
product = await service.filter_one(sku='ABC123')
exists = await service.exists(sku='ABC123')
count = await service.count(status='active')
```

### Filter with Operators

```python
# Sync
adults = service.filter(age__gte=18, status='active')
cheap_products = service.filter(price__lt=100, stock__gt=0)
gmail_users = service.filter(email__ilike='%@gmail.com')

# With pagination and ordering
products = service.filter(
    status='active',
    price__gte=10,
    _limit=20,
    _offset=40,
    _order_by='-created_at'
)

# Async
adults = await service.filter(age__gte=18, status='active')
cheap_products = await service.filter(price__lt=100, stock__gt=0)
gmail_users = await service.filter(email__ilike='%@gmail.com')
```

### Pagination

```python
# Sync
products, meta = service.paginate(page=1, per_page=20)
products, meta = service.paginate(
    page=2,
    per_page=20,
    status='active',
    price__gte=10
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

# Async
products, meta = await service.paginate(page=1, per_page=20)
products, meta = await service.paginate(
    page=2,
    per_page=20,
    status='active',
    price__gte=10
)
```

### Eager Loading (Load Relationships)

Services support eager loading to prevent N+1 query problems. The service layer passes `load_relations` parameters to the underlying repository.

**Basic Usage:**
```python
# Sync - load user with posts
user = service.find(1, load_relations=[selectinload(User.posts)])

# Async - load user with posts
user = await service.find(1, load_relations=[selectinload(User.posts)])

# Access relationships without additional queries
print(user.posts)  # Already loaded!
```

**Multiple Relationships:**
```python
# Sync
invoice = service.find(
    invoice_id,
    load_relations=[selectinload(Invoice.client), selectinload(Invoice.items), selectinload(Invoice.payments)]
)

# Async
invoice = await service.find(
    invoice_id,
    load_relations=[selectinload(Invoice.client), selectinload(Invoice.items), selectinload(Invoice.payments)]
)

# All relationships loaded
print(invoice.client.name)
print(len(invoice.items))
print(invoice.payments)
```

**Nested Relationships:**
```python
# Sync - load nested data
invoices = service.get_all(load_relations=[
    selectinload(Invoice.client),              # Load client
    selectinload(Invoice.items).selectinload(InvoiceItem.product),       # Load items and their products
    selectinload(Invoice.items).selectinload(InvoiceItem.product).selectinload(Product.Category)  # Load products and their categories
])

# Async
invoices = await service.get_all(load_relations=[
    selectinload(Invoice.client),              # Load client
    selectinload(Invoice.items).selectinload(InvoiceItem.product),       # Load items and their products
    selectinload(Invoice.items).selectinload(InvoiceItem.product).selectinload(Product.Category)  # Load products and their categories
])

# Access nested data without N+1
for invoice in invoices:
    for item in invoice.items:
        print(f"{item.product.name} - {item.product.category.name}")
```

**With Filtering:**
```python
# Sync
invoices = service.filter(
    status='paid',
    _load_relations=[selectinload(Invoice.client), selectinload(Invoice.items)]
)

# Async
invoices = await service.filter(
    status='paid',
    _load_relations=[selectinload(Invoice.client), selectinload(Invoice.items)]
)
```

**With Pagination:**
```python
# Sync
invoices, meta = service.paginate(
    page=1,
    per_page=20,
    _load_relations=[selectinload(Invoice.client), selectinload(Invoice.items).selectinload(InvoiceItem.product)]
)

# Async
invoices, meta = await service.paginate(
    page=1,
    per_page=20,
    _load_relations=[selectinload(Invoice.client), selectinload(Invoice.items).selectinload(InvoiceItem.product)]
)
```

**All Service Methods Support Eager Loading:**
```python
# Sync
user = service.find(id, load_relations=[selectinload(User.posts)])
user = service.find_or_fail(id, load_relations=[selectinload(User.posts)])
users = service.get_all(load_relations=[selectinload(User.posts)])
users = service.filter(status='active', _load_relations=[selectinload(User.posts)])
users, meta = service.paginate(page=1, per_page=20, _load_relations=[selectinload(User.posts)])
user = service.filter_one(email='john@test.com', _load_relations=[selectinload(User.posts)])

# Async (same API with await)
user = await service.find(id, load_relations=[selectinload(User.posts)])
user = await service.find_or_fail(id, load_relations=[selectinload(User.posts)])
users = await service.get_all(load_relations=[selectinload(User.posts)])
users = await service.filter(status='active', _load_relations=[selectinload(User.posts)])
users, meta = await service.paginate(page=1, per_page=20, _load_relations=[selectinload(User.posts)])
user = await service.filter_one(email='john@test.com', _load_relations=[selectinload(User.posts)])
```

**With Response Schema Mapping:**
```python
# Service with response schema
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=UserResponse)

# Eager loading works with response mapping
user_response = service.find(1, load_relations=[selectinload(User.posts)])
# Returns UserResponse, relationships loaded before mapping
```

**Performance Note:**
- Service layer simply delegates `load_relations` to repository
- All N+1 prevention happens at repository level
- No performance overhead from service layer
- See [Database Documentation](database.md) for detailed performance info

### Create Operations

```python
# Sync - single record
product = service.create(ProductCreate(name="Widget", price=9.99))

# Multiple records
products = service.create_many([
    ProductCreate(name="Widget 1", price=9.99),
    ProductCreate(name="Widget 2", price=12.99)
])

# Without auto-commit
product = service.create(data, commit=False)
service.commit()

# Async
product = await service.create(ProductCreate(name="Widget", price=9.99))
products = await service.create_many([...])
product = await service.create(data, commit=False)
await service.commit()
```

### Update Operations

```python
# Sync - single record
product = service.update(1, ProductUpdate(price=12.99))

# Multiple records
count = service.update_many(
    filters={'status': 'pending'},
    data=ProductUpdate(status='active')
)

# Async
product = await service.update(1, ProductUpdate(price=12.99))
count = await service.update_many(
    filters={'status': 'pending'},
    data=ProductUpdate(status='active')
)
```

### Delete Operations

```python
# Sync
deleted = service.delete(1)                  # Soft delete if supported
deleted = service.delete(1, force=True)      # Force hard delete
count = service.delete_many({'status': 'inactive'})

# Async
deleted = await service.delete(1)
deleted = await service.delete(1, force=True)
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

Automatic slug generation for services that need URL-friendly slugs.

### Setup

```python
from fastkit_core.services import BaseCrudService, SlugServiceMixin
from models import Article
from schemas import ArticleCreate, ArticleUpdate, ArticleResponse

# Sync service
class ArticleService(SlugServiceMixin, BaseCrudService[
    Article,
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse
]):
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=ArticleResponse)
    
    def before_create(self, data: dict) -> dict:
        """Generate slug from title."""
        data['slug'] = self.generate_slug(data['title'])
        return data
    
    def before_update(self, id: int, data: dict) -> dict:
        """Regenerate slug if title changed."""
        if 'title' in data:
            data['slug'] = self.generate_slug(
                data['title'],
                exclude_id=id  # Exclude current record from uniqueness check
            )
        return data
```

### Async Service

```python
from fastkit_core.services import AsyncBaseCrudService, SlugServiceMixin

class ArticleService(SlugServiceMixin, AsyncBaseCrudService[
    Article,
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse
]):
    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=ArticleResponse)
    
    async def before_create(self, data: dict) -> dict:
        """Generate slug from title."""
        data['slug'] = await self.async_generate_slug(data['title'])
        return data
    
    async def before_update(self, id: int, data: dict) -> dict:
        """Regenerate slug if title changed."""
        if 'title' in data:
            data['slug'] = await self.async_generate_slug(
                data['title'],
                exclude_id=id
            )
        return data
```

### Features

```python
# Basic slugification (static method - no DB check)
slug = SlugServiceMixin.slugify("Hello World!")
# "hello-world"

slug = SlugServiceMixin.slugify("Café au Lait")
# "cafe-au-lait"

# Sync - with uniqueness check
slug = service.generate_slug("Hello World")
# "hello-world"

# If "hello-world" exists, appends number
slug = service.generate_slug("Hello World")
# "hello-world-2"

# Async - with uniqueness check
slug = await service.async_generate_slug("Hello World")

# Custom parameters
slug = service.generate_slug(
    text="My Article Title",
    slug_field='slug',           # Field name (default: 'slug')
    exclude_id=5,                # Exclude current record (for updates)
    separator='_',               # Separator (default: '-')
    max_length=100               # Max length (default: 255)
)
# "my_article_title"

# Custom slug field
slug = service.generate_slug(
    text="Product Name",
    slug_field='url_slug'  # Use different field
)
```

### Safety Features

- **Uniqueness** - Automatically checks database and appends numbers
- **Unicode handling** - Converts accented characters to ASCII
- **Length limiting** - Respects max_length parameter
- **Safety limit** - After 1000 duplicates, adds random suffix to prevent infinite loops

---

<a name="advanced-patterns"></a>
## Advanced Patterns

### Custom Business Methods

```python
class OrderService(BaseCrudService[Order, OrderCreate, OrderUpdate, OrderResponse]):
    
    def cancel_order(self, order_id: int, reason: str) -> OrderResponse:
        """Custom business method."""
        order = self.find_or_fail(order_id)
        
        if order.status == 'shipped':
            raise ValueError("Cannot cancel shipped orders")
        
        # Update with business logic
        return self.update(order_id, OrderUpdate(
            status='cancelled',
            cancel_reason=reason,
            cancelled_at=datetime.now()
        ))
    
    def get_user_orders(self, user_id: int) -> list[OrderResponse]:
        """Get all orders for a user."""
        return self.filter(user_id=user_id, _order_by='-created_at')
    
    def get_pending_orders(self) -> list[OrderResponse]:
        """Get all pending orders."""
        return self.filter(status='pending')
```

### Async Custom Methods

```python
class OrderService(AsyncBaseCrudService[Order, OrderCreate, OrderUpdate, OrderResponse]):
    
    async def cancel_order(self, order_id: int, reason: str) -> OrderResponse:
        """Custom business method (async)."""
        order = await self.find_or_fail(order_id)
        
        if order.status == 'shipped':
            raise ValueError("Cannot cancel shipped orders")
        
        return await self.update(order_id, OrderUpdate(
            status='cancelled',
            cancel_reason=reason,
            cancelled_at=datetime.now()
        ))
    
    async def get_user_orders(self, user_id: int) -> list[OrderResponse]:
        """Get all orders for a user (async)."""
        return await self.filter(user_id=user_id, _order_by='-created_at')
```

### Multiple Services Coordination

```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    def __init__(
        self,
        repository: Repository,
        profile_service: 'ProfileService'
    ):
        super().__init__(repository, response_schema=UserResponse)
        self.profile_service = profile_service
    
    def after_create(self, instance: User) -> None:
        """Create related profile after user creation."""
        self.profile_service.create(ProfileCreate(
            user_id=instance.id,
            display_name=instance.name
        ))

# In dependency
def get_user_service(
    session: Session = Depends(get_db)
) -> UserService:
    user_repo = Repository(User, session)
    profile_repo = Repository(Profile, session)
    profile_service = ProfileService(profile_repo)
    return UserService(user_repo, profile_service)
```

### Complex Validation

```python
class ArticleService(BaseCrudService[Article, ArticleCreate, ArticleUpdate, ArticleResponse]):
    
    def validate_create(self, data: ArticleCreate) -> None:
        """Complex validation logic."""
        # Check slug uniqueness
        if self.exists(slug=data.slug):
            raise ValueError("Slug already exists")
        
        # Check category exists
        if not category_exists(data.category_id):
            raise ValueError("Category not found")
        
        # Check user permissions
        if not can_create_article():
            raise ValueError("Insufficient permissions")
        
        # Content validation
        if len(data.content) < 100:
            raise ValueError("Article content too short")
        
        # Check for spam
        if is_spam(data.content):
            raise ValueError("Content detected as spam")
```

### Event Publishing

```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    def __init__(self, repository: Repository, event_bus: EventBus):
        super().__init__(repository, response_schema=UserResponse)
        self.event_bus = event_bus
    
    def after_create(self, instance: User) -> None:
        """Publish event after creation."""
        self.event_bus.publish('user.created', {
            'user_id': instance.id,
            'email': instance.email,
            'created_at': instance.created_at
        })
    
    def after_update(self, instance: User) -> None:
        """Publish event after update."""
        self.event_bus.publish('user.updated', {
            'user_id': instance.id,
            'updated_at': instance.updated_at
        })
```

---

<a name="best-practices"></a>
## Best Practices

### 1. Keep Services Focused

✅ **Good:**
```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    """Handles user-related operations only."""
    
    def change_password(self, user_id: int, new_password: str) -> None:
        """User-specific business logic."""
        pass

class OrderService(BaseCrudService[Order, OrderCreate, OrderUpdate, OrderResponse]):
    """Handles order-related operations only."""
    
    def cancel_order(self, order_id: int) -> None:
        """Order-specific business logic."""
        pass
```

❌ **Bad:**
```python
class ApplicationService(BaseCrudService):
    """Handles everything - too broad."""
    
    def create_user(self, data): pass
    def create_order(self, data): pass
    def process_payment(self, data): pass
```

### 2. Use Validation Hooks

✅ **Good:**
```python
class ProductService(BaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):
    
    def validate_create(self, data: ProductCreate) -> None:
        if self.exists(sku=data.sku):
            raise ValueError("SKU exists")
        
        if data.price < 0:
            raise ValueError("Invalid price")
```

❌ **Bad:**
```python
@app.post("/products")
def create_product(data: ProductCreate, service: ProductService):
    # Validation in controller - wrong place!
    if service.exists(sku=data.sku):
        raise ValueError("SKU exists")
    
    return service.create(data)
```

### 3. Use Response Schemas

✅ **Good:**
```python
class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    # password excluded automatically!
    
    class Config:
        from_attributes = True

class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    def __init__(self, repository: Repository):
        super().__init__(repository, response_schema=UserResponse)
```

❌ **Bad:**
```python
@app.get("/users/{user_id}")
def get_user(user_id: int, service: UserService):
    user = service.find(user_id)
    # Manually excluding sensitive fields - error-prone!
    return user.to_dict(exclude=['password', 'secret_token'])
```

### 4. Use Lifecycle Hooks for Side Effects

✅ **Good:**
```python
class UserService(BaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    def after_create(self, instance: User) -> None:
        send_welcome_email(instance.email)
        create_user_profile(instance.id)
```

❌ **Bad:**
```python
@app.post("/users")
def create_user(data: UserCreate, service: UserService):
    user = service.create(data)
    # Side effects in controller - wrong place!
    send_welcome_email(user.email)
    return user
```

### 5. Handle Async Properly

✅ **Good:**
```python
class UserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    async def after_create(self, instance: User) -> None:
        await send_welcome_email_async(instance.email)
        await create_profile_async(instance.id)
```

❌ **Bad:**
```python
class UserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    
    async def after_create(self, instance: User) -> None:
        # Blocking calls in async service!
        send_welcome_email(instance.email)  # Should be async
        time.sleep(1)  # Should be asyncio.sleep()
```

### 6. Use Dependency Injection

✅ **Good:**
```python
def get_user_service(
    session: Session = Depends(get_db)
) -> UserService:
    repository = Repository(User, session)
    return UserService(repository)

@app.post("/users")
def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    return service.create(data)
```

### 7. Transaction Management

✅ **Good:**
```python
async def transfer_money(
    from_user_id: int,
    to_user_id: int,
    amount: float,
    service: AccountService
):
    try:
        from_account = await service.find_or_fail(from_user_id)
        to_account = await service.find_or_fail(to_user_id)
        
        await service.update(
            from_user_id,
            {'balance': from_account.balance - amount},
            commit=False
        )
        
        await service.update(
            to_user_id,
            {'balance': to_account.balance + amount},
            commit=False
        )
        
        await service.commit()
    except Exception:
        await service.rollback()
        raise
```

### 8. Error Handling

✅ **Good:**
```python
class ProductService(BaseCrudService[Product, ProductCreate, ProductUpdate, ProductResponse]):
    
    def validate_create(self, data: ProductCreate) -> None:
        if self.exists(sku=data.sku):
            raise ValueError("Product with this SKU already exists")
        
        if data.price <= 0:
            raise ValueError("Price must be greater than zero")

@app.post("/products")
def create_product(data: ProductCreate, service: ProductService = Depends(...)):
    try:
        return service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

<a name="api-reference"></a>
## API Reference

### BaseCrudService

```python
class BaseCrudService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    def __init__(
        repository: Repository,
        response_schema: Type[ResponseSchemaType] | None = None
    )
```

### AsyncBaseCrudService

```python
class AsyncBaseCrudService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    def __init__(
        repository: AsyncRepository,
        response_schema: Type[ResponseSchemaType] | None = None
    )
```

### Validation Hooks

**Sync:**
```python
def validate_create(data: CreateSchemaType) -> None
def validate_update(id: Any, data: UpdateSchemaType) -> None
```

**Async:**
```python
async def validate_create(data: CreateSchemaType) -> None
async def validate_update(id: Any, data: UpdateSchemaType) -> None
```

### Lifecycle Hooks

**Sync:**
```python
def before_create(data: dict) -> dict
def after_create(instance: ModelType) -> None
def before_update(id: Any, data: dict) -> dict
def after_update(instance: ModelType) -> None
def before_delete(id: Any) -> None
def after_delete(id: Any) -> None
```

**Async:**
```python
async def before_create(data: dict) -> dict
async def after_create(instance: ModelType) -> None
async def before_update(id: Any, data: dict) -> dict
async def after_update(instance: ModelType) -> None
async def before_delete(id: Any) -> None
async def after_delete(id: Any) -> None
```

### Read Operations

**Sync:**
```python
def find(
    id: Any,
    load_relations: list[str] | None = None
) -> ResponseSchemaType | ModelType | None

def find_or_fail(
    id: Any,
    load_relations: list[str] | None = None
) -> ResponseSchemaType | ModelType

def get_all(
    limit: int | None = None,
    load_relations: list[str] | None = None
) -> list[ResponseSchemaType | ModelType]

def filter(
    _limit=None,
    _offset=None,
    _order_by=None,
    _load_relations: list[str] | None = None,
    **filters
) -> list[ResponseSchemaType | ModelType]

def filter_one(
    _load_relations: list[str] | None = None,
    **filters
) -> ResponseSchemaType | ModelType | None

def paginate(
    page=1,
    per_page=20,
    _order_by: str | None = None,
    _load_relations: list[str] | None = None,
    **filters
) -> tuple[list[ResponseSchemaType | ModelType], dict]

def exists(**filters) -> bool
def count(**filters) -> int
```

**Async:**
```python
async def find(
    id: Any,
    load_relations: list[str] | None = None
) -> ResponseSchemaType | ModelType | None

async def find_or_fail(
    id: Any,
    load_relations: list[str] | None = None
) -> ResponseSchemaType | ModelType

async def get_all(
    limit: int | None = None,
    load_relations: list[str] | None = None
) -> list[ResponseSchemaType | ModelType]

async def filter(
    _limit=None,
    _offset=None,
    _order_by=None,
    _load_relations: list[str] | None = None,
    **filters
) -> list[ResponseSchemaType | ModelType]

async def filter_one(
    _load_relations: list[str] | None = None,
    **filters
) -> ResponseSchemaType | ModelType | None

async def paginate(
    page=1,
    per_page=20,
    _order_by: str | None = None,
    _load_relations: list[str] | None = None,
    **filters
) -> tuple[list[ResponseSchemaType | ModelType], dict]

async def exists(**filters) -> bool
async def count(**filters) -> int
```

### Create Operations

**Sync:**
```python
def create(data: CreateSchemaType, commit=True) -> ResponseSchemaType | ModelType
def create_many(data_list: list[CreateSchemaType], commit=True) -> list[ResponseSchemaType | ModelType]
```

**Async:**
```python
async def create(data: CreateSchemaType, commit=True) -> ResponseSchemaType | ModelType
async def create_many(data_list: list[CreateSchemaType], commit=True) -> list[ResponseSchemaType | ModelType]
```

### Update Operations

**Sync:**
```python
def update(id: Any, data: UpdateSchemaType, commit=True) -> ResponseSchemaType | ModelType | None
def update_many(filters: dict, data: UpdateSchemaType, commit=True) -> int
```

**Async:**
```python
async def update(id: Any, data: UpdateSchemaType, commit=True) -> ResponseSchemaType | ModelType | None
async def update_many(filters: dict, data: UpdateSchemaType, commit=True) -> int
```

### Delete Operations

**Sync:**
```python
def delete(id: Any, commit=True, force=False) -> bool
def delete_many(filters: dict, commit=True) -> int
```

**Async:**
```python
async def delete(id: Any, commit=True, force=False) -> bool
async def delete_many(filters: dict, commit=True) -> int
```

### Transaction Management

**Sync:**
```python
def commit() -> None
def rollback() -> None
def flush() -> None
```

**Async:**
```python
async def commit() -> None
async def rollback() -> None
async def flush() -> None
```

### SlugServiceMixin

```python
class SlugServiceMixin:
    @staticmethod
    def slugify(text: str, separator: str = '-', max_length: int = 255) -> str
    
    # Sync
    def generate_slug(
        text: str,
        slug_field: str = 'slug',
        exclude_id: Optional[Any] = None,
        separator: str = '-',
        max_length: int = 255
    ) -> str
    
    # Async
    async def async_generate_slug(
        text: str,
        slug_field: str = 'slug',
        exclude_id: Optional[Any] = None,
        separator: str = '-',
        max_length: int = 255
    ) -> str
```

---

## Complete Example

```python
# models.py
from fastkit_core.database import Base, IntIdMixin, TimestampMixin, SlugMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Text, JSON

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
    
    class Config:
        from_attributes = True
```

```python
# services.py
from fastkit_core.services import AsyncBaseCrudService, SlugServiceMixin
from fastkit_core.database import AsyncRepository
from models import Article
from schemas import ArticleCreate, ArticleUpdate, ArticleResponse

class ArticleService(
    SlugServiceMixin,
    AsyncBaseCrudService[Article, ArticleCreate, ArticleUpdate, ArticleResponse]
):
    """Article service with slug generation."""
    
    def __init__(self, repository: AsyncRepository):
        super().__init__(repository, response_schema=ArticleResponse)
    
    async def validate_create(self, data: ArticleCreate) -> None:
        """Validate article creation."""
        # Check author exists
        if not await author_exists(data.author_id):
            raise ValueError("Author not found")
        
        # Check category exists
        if not await category_exists(data.category_id):
            raise ValueError("Category not found")
    
    async def before_create(self, data: dict) -> dict:
        """Generate slug and set defaults."""
        data['slug'] = await self.async_generate_slug(data['title'])
        return data
    
    async def before_update(self, id: int, data: dict) -> dict:
        """Regenerate slug if title changed."""
        if 'title' in data:
            data['slug'] = await self.async_generate_slug(
                data['title'],
                exclude_id=id
            )
        return data
    
    async def after_create(self, instance: Article) -> None:
        """Update search index after creation."""
        await search_index.add_article_async(instance)
    
    async def after_update(self, instance: Article) -> None:
        """Update cache and search index."""
        await cache.delete_async(f'article:{instance.id}')
        await search_index.update_article_async(instance)
    
    async def publish(self, article_id: int) -> ArticleResponse:
        """Publish article."""
        article = await self.find_or_fail(article_id)
        
        if article.status == 'published':
            raise ValueError("Article already published")
        
        return await self.update(article_id, ArticleUpdate(
            status='published'
        ))
```

```python
# main.py
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastkit_core.database import (
    init_async_database,
    shutdown_async_database,
    get_async_db,
    AsyncRepository
)
from fastkit_core.http import success_response
from fastkit_core.config import ConfigManager
configuration = ConfigManager(modules=['database'])
init_async_database(configuration)

app = FastAPI()

async def get_article_service(
    session: AsyncSession = Depends(get_async_db)
) -> ArticleService:
    repository = AsyncRepository(Article, session)
    return ArticleService(repository)

@app.post("/articles", status_code=201)
async def create_article(
    article: ArticleCreate,
    service: ArticleService = Depends(get_article_service)
):
    article_response = await service.create(article)
    return success_response(
        data=article_response.model_dump(),
        message="Article created successfully"
    )

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
        status=status
    )
    
    return {
        'items': [a.model_dump() for a in articles],
        'pagination': meta
    }

@app.get("/articles/{article_id}")
async def get_article(
    article_id: int,
    service: ArticleService = Depends(get_article_service)
):
    article = await service.find_or_fail(article_id)
    return success_response(data=article.model_dump())

@app.put("/articles/{article_id}")
async def update_article(
    article_id: int,
    article: ArticleUpdate,
    service: ArticleService = Depends(get_article_service)
):
    updated = await service.update(article_id, article)
    return success_response(
        data=updated.model_dump(),
        message="Article updated successfully"
    )

@app.post("/articles/{article_id}/publish")
async def publish_article(
    article_id: int,
    service: ArticleService = Depends(get_article_service)
):
    published = await service.publish(article_id)
    return success_response(
        data=published.model_dump(),
        message="Article published successfully"
    )

@app.delete("/articles/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    service: ArticleService = Depends(get_article_service)
):
    await service.delete(article_id)
```

---

## Next Steps

Now that you understand services, explore:

- **[Database](database.md)** - Learn about the repository pattern
- **[Validation](validation.md)** - Schema validation
- **[HTTP](http_utilities.md)** - Response formatting