# FastKit Core

## Introduction

FastKit Core is an open-source, lightweight toolkit developed for the FastAPI framework. It provides common patterns, code structure, and infrastructure solutions following modern Python and FastAPI conventions.

We believe that software development is an enjoyable and creative experience, so developers should focus on building features, not infrastructure. That is only possible when developers have standardized, well-tested, and reliable infrastructure. FastKit Core provides the patterns and structure so you can do exactly that.

FastAPI is fast and flexible by design, but it is intentionally minimal — you build the structure yourself. FastKit Core provides that structure with production-ready patterns:

- **Repository Pattern** for database operations
- **Service Layer** for business logic
- **Multi-language support** built into models and translation files
- **Validation** with structured and translated error messages
- **HTTP Utilities** for consistent API responses

Think of it as **FastAPI with batteries included** — inspired by Laravel's DX and Django's patterns, built specifically for FastAPI.

**Not a framework. Not a replacement. Just FastAPI with structure.**

Because of these improvements, FastKit Core enables faster development and more reliable software, whether you use a monolith or microservice architecture.

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

- **Faster Development**  
  Stop building infrastructure. Start building features.

- **Production Ready**  
  Patterns proven in real-world applications, not experimental code.

- **Unique Features**  
  TranslatableMixin for effortless multi-language models.

- **Zero Vendor Lock-in**  
  Pure FastAPI underneath. Use what you need, skip what you don't.

- **Great Developer Experience**  
  Inspired by Laravel and Django, built for FastAPI's modern Python.

## Performance Considerations

FastKit Core adds **only 3-4ms overhead** while providing:

- Repository Pattern
- Service Layer with Hooks
- Automatic Validation
- Standardized API Responses
- Better Developer Experience
- Faster Development

## Benchmark Details

- **Test Duration**: 60 seconds
- **Concurrent Users**: 100
- **Database**: PostgreSQL 16
- **Environment**: Same Python process (fair comparison)

### Performance Impact

| Metric          | Native FastAPI | FastKit Core | Impact     |
| --------------- | -------------- | ------------ | ---------- |
| Throughput      | 695 RPS        | 685 RPS      | **-1.5%**  |
| Avg Response    | 6.0ms          | 9.4ms        | **+3.4ms** |
| Median Response | 5ms            | 8ms          | **+3ms**   |

### Conclusion

FastKit Core adds **< 5ms overhead** (< 2% in production) while providing
enterprise-grade architecture and significantly better developer experience.

**Perfect balance of performance and productivity!**

---

## A Quick Look

This is a simplified example to illustrate structure and separation of concerns. Here's what FastKit Core looks like in action:

**Without FastKit (Raw FastAPI):**

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User

app = FastAPI()

@app.get("/users")
def list_users(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return {
        "data": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "age": u.age
            }
            for u in users
        ]
    }
```

**With FastKit Core:**

```python
from fastapi import FastAPI, Depends
from fastkit_core.services import BaseCrudService
from fastkit_core.http import paginated_response
from models import User, UserResponse
from services import UserService, get_user_service
from sqlalchemy.orm import Session

app = FastAPI()

@app.get("/users")
def list_users(
    page: int = 1,
    per_page: int = 20,
    service: UserService = Depends(get_user_service)
):
    users, meta = service.paginate(page=page, per_page=per_page)
    return paginated_response(
        items=[UserResponse.from_orm(u) for u in users],
        pagination=meta
    )
```

**Notice:**

- Cleaner, more organized code
- Built-in pagination with metadata
- Standardized response format
- Reusable service layer
- Same FastAPI you know and love
