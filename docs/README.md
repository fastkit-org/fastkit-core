# FastKit Core Documentation

Welcome to the FastKit Core documentation! This documentation will help you build production-ready FastAPI applications with proven patterns and best practices.

## 📚 Table of Contents

### Getting Started
- **[Landing Page](landing.md)** - What is FastKit Core and why use it?
- **[Installation](installation.md)** - Install FastKit Core and set up your environment
- **[Quick Start](quick_start.md)** - Build your first API in 5 minutes

### Core Concepts
- **[Configuration](configuration.md)** - Environment variables, config management, and settings
- **[Database](database.md)** - Models, repository pattern, migrations, and queries
- **[Services](services.md)** - Business logic layer with hooks and validation
- **[Validation](validation.md)** - Schema validation and error handling
- **[HTTP Utilities](http_utilities.md)** - Standardized responses, exceptions, and middleware
- **[Translations](translations.md)** - Multi-language support and i18n

---

## 🚀 Quick Navigation

### New to FastKit Core?

1. Start with the **[Landing Page](landing.md)** to understand what FastKit Core is
2. Follow the **[Installation](installation.md)** guide to set up your environment
3. Complete the **[Quick Start](quick_start.md)** to build your first API in 5 minutes
4. Deep dive into **[Database](database.md)** and **[Services](services.md)** for core patterns

### Looking for Specific Features?

| Feature | Documentation                                |
|---------|----------------------------------------------|
| Database setup and connections | [Configuration](configuration.md)               |
| Models and ORM | [Database](database.md)                         |
| CRUD operations | [Database](database.md) → Repository Pattern    |
| Business logic | [Services](services.md)                         |
| Input validation | [Validation](validation.md)                     |
| API responses | [HTTP Utilities](http_utilities.md)          |
| Multi-language content | [Database](database.md) → TranslatableMixin  |
| Translation files | [Translations](translations.md)              |
| Async support | [Database](database.md) → Async Support      |
| Read replicas | [Database](database.md) → Session Management |

---

## 📖 Documentation Guide

### [Landing Page](landing.md)
**What you'll learn:**
- What FastKit Core is and who it's for
- Why use FastKit Core over plain FastAPI
- Performance benchmarks
- Quick comparison with raw FastAPI

**Best for:** Understanding the vision and deciding if FastKit Core is right for you

---

### [Installation](installation.md)
**What you'll learn:**
- System requirements
- Installation methods (pip, Poetry, Pipenv)
- Database driver setup
- Verification steps

**Best for:** Getting FastKit Core installed and ready to use

---

### [Quick Start](quick_start.md)
**What you'll learn:**
- Build a complete Todo API in 5 minutes
- Project structure
- Database models with mixins
- Service layer
- API endpoints with validation

**Best for:** Hands-on learning and getting started quickly

---

### [Configuration](configuration.md)
**What you'll learn:**
- Environment variable management
- Configuration modules
- Database connections
- Multiple environment setup
- Best practices for config management

**Best for:** Setting up your application configuration properly

---

### [Database](database.md)
**What you'll learn:**
- Base models and mixins (IntId, UUID, Timestamps, SoftDelete, Slug, Publishable)
- Repository pattern for data access
- Django-style filtering with operators
- Pagination
- TranslatableMixin for multi-language models
- Async/sync database operations
- Read replicas and connection management
- Session management

**Best for:** Understanding data layer architecture and ORM usage

---

### [Services](services.md)
**What you'll learn:**
- BaseCrudService for business logic
- AsyncBaseCrudService for async operations
- Lifecycle hooks (before_create, after_update, etc.)
- Validation hooks
- Response schema mapping
- SlugServiceMixin for automatic slug generation
- Transaction management
- Best practices for service layer

**Best for:** Organizing business logic and creating maintainable code

---

### [Validation](validation.md)
**What you'll learn:**
- Pydantic schema validation
- Custom validation rules
- Error message formatting
- Multi-language error messages
- Field validators
- Model validators

**Best for:** Handling input validation and error messages

---

### [HTTP Utilities](http_utilities.md)
**What you'll learn:**
- Standardized response formats
- Success and error responses
- Pagination responses
- Exception handling
- Custom exceptions
- Middleware patterns

**Best for:** Creating consistent API responses and error handling

---

### [Translations](translations.md)
**What you'll learn:**
- Translation file structure
- Loading and managing translations
- Multi-language API responses
- Dynamic translation
- Fallback languages
- Best practices for i18n

**Best for:** Building multi-language applications

---

## 🎯 Common Use Cases

### Building a CRUD API
1. Read [Quick Start](quick_start.md)
2. Study [Database](database.md) → Repository Pattern
3. Learn [Services](services.md) → BaseCrudService
4. Implement [Validation](validation.md)
5. Use [HTTP Utilities](http_utilities.md) for responses

### Multi-Language Application
1. Configure [Database](database.md) → TranslatableMixin
2. Set up [Translations](translations.md) files
3. Use [Services](services.md) with locale handling
4. Return localized responses via [HTTP Utilities](http_utilities.md)

### Complex Business Logic
1. Design models in [Database](database.md)
2. Create services with [Services](services.md) → Lifecycle Hooks
3. Add validation with [Services](services.md) → Validation Hooks
4. Handle errors with [HTTP Utilities](http_utilities.md)

### High-Performance API
1. Set up [Database](database.md) → Read Replicas
2. Use [Database](database.md) → Async Support
3. Implement [Services](services.md) → AsyncBaseCrudService
4. Optimize with [Configuration](configuration.md) → Database Pooling

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────┐
│           FastAPI Application           │
└─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────┐        ┌──────────────┐
│ HTTP Layer   │        │  Validation  │
│ (Responses,  │        │  (Schemas)   │
│  Exceptions) │        │              │
└──────────────┘        └──────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
        ┌──────────────────────┐
        │   Service Layer      │
        │ (Business Logic,     │
        │  Hooks, Validation)  │
        └──────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────┐        ┌──────────────┐
│  Repository  │        │ Translations │
│  (Data       │        │ (i18n)       │
│   Access)    │        │              │
└──────────────┘        └──────────────┘
        │
        ▼
┌──────────────────────┐
│   Database Layer     │
│ (Models, Mixins,     │
│  SQLAlchemy)         │
└──────────────────────┘
```

**Layer responsibilities:**
- **HTTP Layer** - Request/response handling, standardized formats
- **Validation** - Input validation, schema definitions
- **Service Layer** - Business logic, hooks, orchestration
- **Repository** - Data access, queries, transactions
- **Translations** - Multi-language support
- **Database Layer** - ORM models, relationships, migrations

---

## 🔍 Finding What You Need

### By Topic

**Configuration & Setup**
- [Configuration](configuration.md) - Environment and settings
- [Installation](installation.md) - Getting started

**Data & Database**
- [Database](database.md) - Complete database guide
- Models, Mixins, Repository, Async support

**Business Logic**
- [Services](services.md) - Service layer patterns
- Hooks, Validation, Transaction management

**API Layer**
- [HTTP Utilities](http_utilities.md) - Responses and exceptions
- [Validation](validation.md) - Input validation

**Internationalization**
- [Translations](translations.md) - Translation files
- [Database](database.md) → TranslatableMixin - Multi-language models

### By Experience Level

**Beginner**
1. [Landing Page](landing.md)
2. [Installation](installation.md)
3. [Quick Start](quick_start.md)
4. [Database](database.md) - Base Models section
5. [Services](services.md) - BaseCrudService section

**Intermediate**
1. [Database](database.md) - Mixins and Repository
2. [Services](services.md) - Lifecycle Hooks
3. [Validation](validation.md)
4. [HTTP Utilities](http_utilities.md)
5. [Configuration](configuration.md) - Advanced patterns

**Advanced**
1. [Database](database.md) - Async Support, Read Replicas
2. [Services](services.md) - AsyncBaseCrudService
3. [Database](database.md) - TranslatableMixin
4. [Services](services.md) - Advanced Patterns
5. [Database](database.md) - Connection Manager



## 🤝 Contributing to Documentation

Found an error or want to improve the docs?

1. All documentation is in Markdown format
2. Follow existing style and structure
3. Include code examples
4. Test all code snippets
5. Submit a pull request

---

## 📞 Getting Help

- **Questions?** Check the relevant documentation section first
- **Bug reports?** [GitHub Issues](https://github.com/codevelo-pub/fastkit-core/issues)
- **Discussions?** [GitHub Discussions](https://github.com/codevelo-pub/fastkit-core/discussions)
- **Examples?** [FastKit Examples Repo](https://github.com/codevelo-pub/fastkit-examples)

---

*Last updated: January 2026*