<div align="center">
  <h1>FastKit Core</h1>
  
  [![PyPI version](https://badge.fury.io/py/fastkit-core.svg)](https://pypi.org/project/fastkit-core/)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![Tests](https://github.com/fastkit/fastkit-core/workflows/Tests/badge.svg)](https://github.com/fastkit/fastkit-core/actions)
  [![Coverage](https://codecov.io/gh/fastkit/fastkit-core/branch/main/graph/badge.svg)](https://codecov.io/gh/fastkit/fastkit-core)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

  
</div>

---
## What is FastKit Core?
We believe that development should be an enjoyable and creative experience, and developer with right tools has to be responsible only for business requirements, so
**FastKit Core is a lightweight toolkit that adds structure and common patterns to FastAPI.**

FastAPI is fast and flexible by design, but it's minimal — you build the structure yourself. FastKit Core provides that structure with production-ready patterns:

- **Repository Pattern** for database operations
- **Service Layer** for business logic
- **Multi-Language Support** built into models and lang files
- **Validation** with translated error messages
- **HTTP Utilities** for consistent API responses

Think of it as **FastAPI with batteries included** — inspired by Laravel's DX and Django's patterns, built specifically for FastAPI.

**Not a framework. Not a replacement. Just FastAPI with structure and improved DX with pythonic**


---

## Why FastKit Core?

## The Problem

When building FastAPI applications, you quickly face questions:

- *How should I structure my project?*
- *Where do repositories go? Do I even need them?*
- *How do I organize business logic?*
- *How do I handle multi-language content in my models?*
- *How do I format validation errors consistently?*
- *How do I standardize API responses?*

Every team solves these differently, leading to inconsistent codebases.

### The Solution

FastKit Core provides **battle-tested patterns** so you don't reinvent the wheel:

✅ **10x Faster Development**  
Stop building infrastructure. Start building features.

✅ **Production Ready**  
Patterns proven in real-world applications, not experimental code.

✅ **Unique Features**  
TranslatableMixin for multi-language models.

✅ **Zero Vendor Lock-in**  
Pure FastAPI underneath. Use what you need, skip what you don't.

✅ **Great Developer Experience**  
Inspired by Laravel and Django, built for FastAPI's modern Python.

### The Result
```python
# Before FastKit: 100+ lines of boilerplate
# With FastKit: 10 lines

class Article(BaseWithTimestamps, TranslatableMixin):
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

[5-minute example to get started]

---

## 📦 Core Modules

### Config
[Example + explanation]

### Database
[Example + explanation]

### Services
[Example + explanation]

### Internationalization (i18n)
[Example + explanation]

### Validation
[Example + explanation]

### HTTP
[Example + explanation]

---

## 📚 Documentation

[Link to full docs]

---

## 🤝 Contributing

[How to contribute]

---

## 📄 License

[MIT License]

