<div align="center">
  <h1>FastKit Core</h1>
  
  [![PyPI version](https://badge.fury.io/py/fastkit-core.svg)](https://pypi.org/project/fastkit-core/)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![CI](https://github.com/codevelo-pub/fastkit-core/actions/workflows/tests.yml/badge.svg)](https://github.com/codevelo-pub/fastkit-core/actions/workflows/tests.yml)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
</div>

---

## What is FastKit Core?

**FastKit Core is a lightweight toolkit that adds structure and common patterns to FastAPI.**

The software development is an enjoyable and creative experience, so we believe developers should focus on building features, not infrastructure. FastKit Core provides the patterns and structure so you can do exactly that.

FastAPI is fast and flexible by design, but it's minimal - you build the structure yourself. FastKit Core provides that structure with production-ready patterns:

- **Repository Pattern** for database operations
- **Service Layer** for business logic
- **Multi-Language Support** built into models and translation files
- **Validation** with translated error messages
- **HTTP Utilities** for consistent API responses

Think of it as **FastAPI with batteries included** — inspired by Laravel's DX and Django's patterns, built specifically for FastAPI.

**Not a framework. Not a replacement. Just FastAPI with structure.**

---
## Who is FastKit Core For?

**FastKit Core is built for developers who:**

**Are Coming from Laravel or Django**
- You love the structure and developer experience, but need FastAPI's performance
- You want familiar concepts (repositories, services, mixins) in modern Python
- You're tired of rebuilding patterns from scratch in every FastAPI project

**Are Building Production Applications**
- You need consistent, maintainable code structure across your team
- You want proven patterns, not experimental approaches
- You're building multi-language applications or complex business logic

**Are New to FastAPI Architecture**
- FastAPI's minimal structure leaves you wondering where to put things
- You need guidance on organizing business logic and database operations
- You want to learn best practices from day one

**Are Leading Development Teams**
- You need to standardize how your team builds FastAPI applications
- You want faster onboarding and more consistent code reviews
- You're tired of every developer having their own architectural approach

**FastKit Core is not for you if:**
- You prefer building everything from scratch and don't want any structure
- You're building simple CRUD APIs with no business logic
- You only need basic FastAPI features (FastAPI alone is perfect for this!)
---

## Why FastKit Core?

### The Problem

When building FastAPI applications, you quickly face questions:

- How should I structure my project?
- Where do repositories go? Do I even need them?
- How do I organize business logic?
- How do I handle multi-language content in my models?
- How do I format validation errors consistently?
- How do I standardize API responses?

Every team solves these differently, leading to inconsistent codebases.

### The Solution

FastKit Core provides **battle-tested patterns** so you don't reinvent the wheel:

- **10x Faster Development**  
Stop building infrastructure. Start building features.

- **Production Ready**  
Patterns proven in real-world applications, not experimental code.

- **Unique Features**  
TranslatableMixin for effortless multi-language models.

- **Zero Vendor Lock-in**  
Pure FastAPI underneath. Use what you need, skip what you don't.

- **Great Developer Experience**  
Inspired by Laravel and Django, built for FastAPI's modern Python.

### The Result
```python
# Before FastKit: 100+ lines of boilerplate
# With FastKit: 10 lines

class Article(BaseWithTimestamps, IntIdMixin, TranslatableMixin):
    __translatable__ = ['title', 'content']
    title: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)

# Multi-language support just works
article.title = "Hello"
article.set_locale('es')
article.title = "Hola"
```

---

## Quick Start

Get up and running in 5 minutes:

### Installation
```bash
pip install fastkit-core
```

### Your First FastKit Application
```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastkit_core.database import BaseWithTimestamps, Repository, get_db, IntIdMixin
from fastkit_core.services import BaseCrudService
from fastkit_core.validation import BaseSchema
from fastkit_core.http import success_response, register_exception_handlers
from fastkit_core.i18n import _
from pydantic import EmailStr

# 1. Define your model
class User(BaseWithTimestamps, IntIdMixin):
    email: Mapped[str]
    name: Mapped[str]

# 2. Define your schema
class UserCreate(BaseSchema, IntIdMixin):
    email: EmailStr
    name: str

# 3. Define your service (business logic)
class UserService(BaseCrudService[User, UserCreate, UserCreate]):
    def validate_create(self, data):
        if self.exists(email=data.email):
            raise ValueError(_('validation.registration.email_is_taken'))

# 4. Create your API
app = FastAPI()
register_exception_handlers(app)

@app.post("/users")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    service = UserService(Repository(User, db))
    user = service.create(data)
    return success_response(data=user.to_dict())

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    service = UserService(Repository(User, db))
    users = service.get_all()
    return success_response(data=[u.to_dict() for u in users])
```

**That's it!** You have a fully functional API with:
- Validation with proper, translatable error messages 
- Business logic separated in services
- Repository pattern for database
- Consistent response formatting
- Timestamps automatically managed

**[See full documentation →](https://fastkit.codevelo.io)**

---

## Core Modules

FastKit Core provides six integrated modules:

### Configuration

Manage application configuration with environment support.
```python
from fastkit_core.config import config

# Load from config files or environment variables
db_host = config('database.HOST', 'localhost')
debug_mode = config('app.DEBUG', False)
```

**Features:**
- Multi-environment support (dev, test, prod)
- `.env` file loading with auto-discovery
- Dot notation access
- Type casting (strings to bool, int, float)

**[Configuration Documentation →](https://fastkit.codevelo.io/modules/config)**

---

### Database

Repository pattern with powerful mixins for common use cases.
```python
from fastkit_core.database import (
    BaseWithTimestamps,
    TranslatableMixin,
    SoftDeleteMixin,
    Repository
)

# Rich model with automatic features
class Article(BaseWithTimestamps, IntIdMixin, TranslatableMixin, SoftDeleteMixin):
    __translatable__ = ['title', 'content']
    
    title: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)
    author_id: Mapped[int]

# Django-style queries
articles = Repository(Article, session).filter(
    author_id__in=[1, 2, 3],
    created_at__gte=datetime(2024, 1, 1),
    _order_by='-created_at'
)

# Multi-language support
article.title = "Hello World"
article.set_locale('es')
article.title = "Hola Mundo"
print(article.to_dict(locale='es'))
```

**Features:**
- Repository pattern with Django-style operators
- TranslatableMixin for multi-language models
- SoftDeleteMixin for data retention
- TimestampsMixin for automatic timestamps
- UUIDMixin, SlugMixin, PublishableMixin
- Multi-connection support with read replicas

**[Database Documentation →](https://fastkit.codevelo.io/modules/database)**

---

### Services

Service layer with validation hooks and lifecycle management.
```python
from fastkit_core.services import BaseCrudService

class UserService(BaseCrudService[User, UserCreate, UserUpdate]):
    
    def validate_create(self, data: UserCreate):
        """Custom validation before creation"""
        if self.exists(email=data.email):
            raise ValueError("Email already exists")
    
    def before_create(self, data: dict) -> dict:
        """Modify data before saving"""
        data['password'] = hash_password(data['password'])
        return data
    
    def after_create(self, instance: User):
        """Actions after creation"""
        send_welcome_email(instance.email)

# Use in routes
service = UserService(Repository(User, session))
user = service.create(user_data)  # All hooks run automatically
```

**Features:**
- BaseCrudService with all CRUD operations
- Validation hooks
- Lifecycle hooks (before/after create, update, delete)
- Transaction management
- Pagination support
- Seamless repository integration

**[Services Documentation →](https://fastkit.codevelo.io/modules/services)**

---

### Internationalization (i18n)

Manage translations with Laravel-style helpers.
```python
from fastkit_core.i18n import _, set_locale

# translations/en.json
# {
#   "messages": {
#     "welcome": "Welcome, {name}!",
#     "goodbye": "Goodbye!"
#   }
# }

set_locale('en')
print(_('messages.welcome', name='John'))  # "Welcome, John!"

set_locale('es')
print(_('messages.welcome', name='Juan'))  # "¡Bienvenido, Juan!"
```

**Features:**
- JSON-based translations
- Pythonic `_()` helper (follows gettext standard)
- Variable replacement
- Locale context (shared with TranslatableMixin)
- Fallback support
- Middleware integration

**[i18n Documentation →](https://fastkit.codevelo.io/modules/i18n)**

---

### Validation

Pydantic schemas with translated error messages and reusable validators.
```python
from pydantic import EmailStr
from fastkit_core.validation import (
    BaseSchema,
    PasswordValidatorMixin,
    UsernameValidatorMixin
)

class UserCreate(BaseSchema, PasswordValidatorMixin, UsernameValidatorMixin):
    email: EmailStr
    username: str  # Validated by UsernameValidatorMixin
    password: str  # Validated by PasswordValidatorMixin

# Validation errors are automatically translated
set_locale('es')
try:
    user = UserCreate(email="invalid", password="weak")
except ValidationError as e:
    errors = BaseSchema.format_errors(e)
    # Returns: {"email": ["Must be valid..."], "password": ["Must be at least..."]}
```

**Features:**
- BaseSchema with Laravel-style error formatting
- Automatic translation of error messages
- Reusable validation mixins
- Customizable error messages per schema
- Field validation rules
- Pydantic v2 compatible

**[Validation Documentation →](https://fastkit.codevelo.io/modules/validation)**

---

### HTTP

Standard response formatting and exception handling.
```python
from fastkit_core.http import (
    success_response,
    paginated_response,
    NotFoundException,
    register_exception_handlers
)

# Register handlers once
app = FastAPI()
register_exception_handlers(app)

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = service.find(user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    
    return success_response(data=user.to_dict())

@app.get("/users")
def list_users(page: int = 1):
    users, pagination = service.paginate(page=page, per_page=20)
    return paginated_response(
        items=[u.to_dict() for u in users],
        pagination=pagination
    )
```

**Features:**
- Standard response formatters
- Automatic exception handling
- Custom exceptions
- Middleware (RequestID, Locale detection)
- Pagination helpers
- CORS configuration

**[HTTP Documentation →](https://fastkit.codevelo.io/modules/http)**

---

# FastKit Core Performance Benchmark

## Results Summary

FastKit Core adds **only 3-4ms overhead** while providing:

- Repository Pattern
- Service Layer with Hooks
- Automatic Validation
- Standardized API Responses
- Better Developer Experience
- 10x Faster Development

## Benchmark Details

- **Test Duration**: 60 seconds
- **Concurrent Users**: 100
- **Database**: PostgreSQL 16
- **Environment**: Same Python process (fair comparison)

### Performance Impact

| Metric | Native FastAPI | FastKit Core | Impact |
|--------|---------------|--------------|--------|
| Throughput | 695 RPS | 685 RPS | **-1.5%** |
| Avg Response | 6.0ms | 9.4ms | **+3.4ms** |
| Median Response | 5ms | 8ms | **+3ms** |
| Failure Rate | 47% | 42% | **-11% better!** |

### Conclusion

FastKit Core adds **< 5ms overhead** (< 2% in production) while providing
enterprise-grade architecture and 10x better developer experience.

**Perfect balance of performance and productivity!** ✨

## Documentation

Complete guides, tutorials, and API reference:  
**[fastkit.codevelo.io](https://fastkit.codevelo.io)**

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

---

## License

FastKit Core is open-source software licensed under the [MIT License](https://opensource.org/license/MIT).

---

## Built by CodeVelo

FastKit is developed and maintained by [Codevelo](https://codevelo.io) for the FastAPI community.