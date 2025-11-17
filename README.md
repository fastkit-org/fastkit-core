<div align="center">
  <h1>⚡ FastKit Core</h1>
  
  <p><strong>The Modern Python Web Framework</strong></p>
  
  <p>Build production-ready APIs 10x faster with FastAPI + DDD patterns</p>
  
  [![PyPI version](https://badge.fury.io/py/fastkit-core.svg)](https://pypi.org/project/fastkit-core/)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![Tests](https://github.com/fastkit/fastkit-core/workflows/Tests/badge.svg)](https://github.com/fastkit/fastkit-core/actions)
  [![Coverage](https://codecov.io/gh/fastkit/fastkit-core/branch/main/graph/badge.svg)](https://codecov.io/gh/fastkit/fastkit-core)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Discord](https://img.shields.io/discord/YOUR_DISCORD_ID?color=7289da&label=Discord&logo=discord&logoColor=ffffff)](https://discord.gg/fastkit)
  
</div>

---

## 🚀 What is FastKit Core?

FastKit Core is the foundation of the FastKit framework - a modern Python web framework that combines the **blazing speed of FastAPI** with the **elegant developer experience of Laravel**.

If you love FastAPI's performance and automatic API documentation, but miss the clean architecture patterns from frameworks like Laravel or Ruby on Rails, FastKit Core is for you.

### The Problem

FastAPI is amazing, but it's minimal by design. You still need to figure out:
- 📁 Project structure
- 🗄️ Database layer patterns
- 🎯 Service layer architecture
- 🔄 Repository pattern implementation
- 🏗️ Dependency injection
- 📦 How to organize growing codebases

### The Solution

FastKit Core provides battle-tested patterns and abstractions that make building production-ready applications faster and more enjoyable.
```python
# Traditional FastAPI - You build everything
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()  # Direct DB access
    return users  # No abstraction

# With FastKit Core - Clean architecture built-in
@app.get("/users")
def get_users(service: UserService = Depends()):
    return service.get_all()  # Business logic in service layer
```

---

## ✨ Key Features

### 🏗️ **Repository Pattern**
Clean data access layer with built-in CRUD operations and query helpers.
```python
from fastkit_core.database import BaseRepository

class UserRepository(BaseRepository[User]):
    def find_by_email(self, email: str) -> Optional[User]:
        return self.first_where(email=email)
    
    def active_users(self) -> List[User]:
        return self.where(is_active=True)

# Usage - it just works!
repo = UserRepository(User, session)
user = repo.find(1)
users = repo.paginate(page=1, per_page=20)
```

### 🎯 **Service Layer**
Encapsulate business logic separate from routes and data access.
```python
from fastkit_core.services import BaseService

class UserService(BaseService[User, UserRepository]):
    def register(self, name: str, email: str, password: str) -> User:
        # Validation
        if self.repository.find_by_email(email):
            raise ValueError("Email already exists")
        
        # Business logic
        hashed_password = hash_password(password)
        
        # Create user
        return self.create({
            "name": name,
            "email": email,
            "password": hashed_password
        })
```

### 📦 **Dependency Injection**
Laravel-inspired container for managing dependencies.
```python
from fastkit_core.container import Container

container = Container()

# Register services
container.singleton(UserRepository, lambda: UserRepository(User, get_db()))
container.bind(UserService, lambda: UserService(container.make(UserRepository)))

# Resolve automatically
service = container.make(UserService)
```

### 🗃️ **Database Abstractions**
SQLAlchemy-based with quality-of-life improvements.
```python
from fastkit_core.database import Base

class User(Base):
    __tablename__ = "users"
    
    name = Column(String(100))
    email = Column(String(255), unique=True)
    # Timestamps added automatically (created_at, updated_at)
```

### 📁 **File Storage**
Local and S3 storage with unified interface.
```python
from fastkit_core.storage import LocalStorage, S3Storage

storage = LocalStorage(path="./uploads")
# or
storage = S3Storage(bucket="my-bucket")

# Same interface for both!
storage.put("avatars/user1.jpg", file_content)
url = storage.url("avatars/user1.jpg")
storage.delete("avatars/user1.jpg")
```

### 🌍 **Internationalization (i18n)**
Multi-language support out of the box.
```python
from fastkit_core.i18n import Translator

translator = Translator(locale="es")
translator.translate("auth.welcome")  # "Bienvenido"
```

### 🧪 **Fully Tested**
95%+ test coverage with comprehensive test suite.

---

## 📦 Installation
```bash
pip install fastkit-core
```

Or with optional dependencies:
```bash
# With S3 storage support
pip install fastkit-core[s3]

# With all optional features
pip install fastkit-core[all]
```

---

## 🎯 Quick Start

### 1. Define Your Model
```python
from fastkit_core.database import Base
from sqlalchemy import Column, String, Boolean

class User(Base):
    __tablename__ = "users"
    
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
```

### 2. Create Repository
```python
from fastkit_core.database import BaseRepository

class UserRepository(BaseRepository[User]):
    def find_active(self) -> List[User]:
        return self.where(is_active=True)
```

### 3. Create Service
```python
from fastkit_core.services import BaseService

class UserService(BaseService[User, UserRepository]):
    def deactivate_user(self, user_id: int) -> User:
        return self.update(user_id, {"is_active": False})
```

### 4. Use in FastAPI Routes
```python
from fastapi import FastAPI, Depends

app = FastAPI()

@app.get("/users")
def list_users(
    page: int = 1,
    service: UserService = Depends()
):
    return service.repository.paginate(page=page, per_page=20)

@app.post("/users")
def create_user(
    name: str,
    email: str,
    service: UserService = Depends()
):
    return service.create({"name": name, "email": email})

@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    service: UserService = Depends()
):
    service.delete(user_id)
    return {"message": "User deleted"}
```

### 5. Run It!
```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for automatic API documentation.

---

## 🏗️ Architecture

FastKit Core promotes clean architecture with clear separation of concerns:
```
┌─────────────────────────────────────────┐
│           Controllers/Routes             │  FastAPI endpoints
│         (HTTP Layer)                     │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│             Services                     │  Business logic
│         (Application Layer)              │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│           Repositories                   │  Data access
│          (Domain Layer)                  │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│            Database                      │  PostgreSQL, MySQL, SQLite
│        (Infrastructure)                  │
└─────────────────────────────────────────┘
```

**Benefits:**
- ✅ **Testability**: Each layer can be tested independently
- ✅ **Maintainability**: Clear separation makes code easier to understand
- ✅ **Scalability**: Easy to extend without touching existing code
- ✅ **Reusability**: Services and repositories can be reused across routes

---

## 📚 Documentation

- [**Getting Started**](https://docs.fastkit.dev/core/getting-started) - Complete beginner's guide
- [**Configuration**](https://docs.fastkit.dev/core/configuration) - Environment and settings
- [**Database & Models**](https://docs.fastkit.dev/core/database) - Working with databases
- [**Repositories**](https://docs.fastkit.dev/core/repositories) - Data access patterns
- [**Services**](https://docs.fastkit.dev/core/services) - Business logic layer
- [**Dependency Injection**](https://docs.fastkit.dev/core/container) - Managing dependencies
- [**File Storage**](https://docs.fastkit.dev/core/storage) - File uploads and management
- [**Internationalization**](https://docs.fastkit.dev/core/i18n) - Multi-language support
- [**API Reference**](https://docs.fastkit.dev/core/api) - Complete API documentation

---

## 🎓 Examples

Check out the [`examples/`](examples/) directory for complete working examples:

- **[Basic CRUD](examples/basic/)** - Simple blog with posts and comments
- **[Authentication](examples/auth/)** - User registration and JWT authentication
- **[File Uploads](examples/files/)** - Image uploads with storage abstraction
- **[Multi-language](examples/i18n/)** - Internationalized API
- **[Full Application](examples/full/)** - Production-ready project structure

---

## 🆚 Comparison

### FastKit Core vs. Plain FastAPI

| Feature | Plain FastAPI | FastKit Core |
|---------|--------------|--------------|
| **API Speed** | ⚡⚡⚡ | ⚡⚡⚡ (Same) |
| **Auto Docs** | ✅ | ✅ (Same) |
| **Repository Pattern** | ❌ (DIY) | ✅ Built-in |
| **Service Layer** | ❌ (DIY) | ✅ Built-in |
| **DI Container** | ⚠️ Basic | ✅ Advanced |
| **Project Structure** | ❌ Up to you | ✅ Defined |
| **File Storage** | ❌ (DIY) | ✅ Built-in |
| **i18n Support** | ❌ (DIY) | ✅ Built-in |
| **Code Generation** | ❌ | ✅ Via CLI |

### FastKit Core vs. Django

| Feature | Django | FastKit Core |
|---------|--------|--------------|
| **Performance** | 🐌 Slower | ⚡⚡⚡ 3x faster |
| **Async Support** | ⚠️ Limited | ✅ Full async |
| **Type Hints** | ❌ No | ✅ Full typing |
| **API Docs** | ❌ (needs DRF) | ✅ Automatic |
| **ORM** | ✅ Great | ✅ SQLAlchemy |
| **Architecture** | ✅ Batteries included | ✅ Clean patterns |
| **Learning Curve** | ⚠️ Steep | ✅ Gentle |

---

## 🤝 Contributing

We love contributions! Whether it's:

- 🐛 Bug reports
- 💡 Feature requests
- 📝 Documentation improvements
- 🔧 Code contributions

Please read our [**Contributing Guide**](CONTRIBUTING.md) to get started.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/fastkit/fastkit-core.git
cd fastkit-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=fastkit_core --cov-report=html

# Format code
black fastkit_core tests
ruff fastkit_core tests

# Type checking
mypy fastkit_core
```

---

## 🌟 Who's Using FastKit?

*Coming soon - be the first to add your project!*

Using FastKit in production? [**Add your project here**](https://github.com/fastkit/fastkit-core/issues/new?template=showcase.md)

---

## 📝 License

FastKit Core is open-source software licensed under the [**MIT License**](LICENSE).

---

## 🙏 Acknowledgments

FastKit Core is inspired by excellent frameworks and libraries:

- [**FastAPI**](https://fastapi.tiangolo.com/) - The foundation we build upon
- [**Laravel**](https://laravel.com/) - Beautiful API design and developer experience
- [**Django**](https://www.djangoproject.com/) - Batteries-included philosophy
- [**Ruby on Rails**](https://rubyonrails.org/) - Convention over configuration
- [**SQLAlchemy**](https://www.sqlalchemy.org/) - Powerful ORM

Special thanks to all [contributors](https://github.com/fastkit/fastkit-core/graphs/contributors) who make FastKit better!

---

## 🔗 Links

- [**Website**](https://fastkit.dev) - Official website
- [**Documentation**](https://docs.fastkit.dev) - Full documentation
- [**PyPI**](https://pypi.org/project/fastkit-core/) - Package repository
- [**GitHub**](https://github.com/fastkit/fastkit-core) - Source code
- [**Discord**](https://discord.gg/fastkit) - Community chat
- [**Twitter**](https://twitter.com/fastkitdev) - Updates and news
- [**Blog**](https://blog.fastkit.dev) - Tutorials and articles

---

## ⭐ Star History

<a href="https://star-history.com/#fastkit/fastkit-core&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=fastkit/fastkit-core&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=fastkit/fastkit-core&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=fastkit/fastkit-core&type=Date" />
  </picture>
</a>

---

<div align="center">
  
**Built with ❤️ by the FastKit team**

[⭐ Star us on GitHub](https://github.com/fastkit/fastkit-core) | [🐦 Follow on Twitter](https://twitter.com/fastkitdev) | [💬 Join Discord](https://discord.gg/fastkit)

</div>
