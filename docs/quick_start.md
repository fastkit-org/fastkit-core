# Quick Start

Build your first FastKit API in 5 minutes! You'll create a working 
Todo API with database operations, validation, and standardized responses.

- [Prerequisites](#prerequisites)
- [Step 1: Project Setup](#step-1-project-setup)
- [Step 2: Configure Database](#step-2-configure-database)
- [Step 3: Create Your Model](#step-3-create-your-model)
- [Step 4: Create Service](#step-4-create-service)
- [Step 5: Create API Endpoints](#step-5-create-api-endpoints)
- [Step 6: Run Your API](#step-6-run-your-api)
- [Test Your API](#test-your-api)
- [What You Built](#what-you-built)
- [Next Steps](#next-steps)

---

<a name="prerequisites"></a>
## Prerequisites

Before starting, make sure you have:

- ✅ Python 3.11+ installed
- ✅ FastKit Core installed (`pip install fastkit-core`)
- ✅ Basic FastAPI knowledge (optional but helpful)

> **New to FastAPI?** No problem! This guide assumes no prior experience.

**Time required:** 5-10 minutes

---

<a name="step-1-project-setup"></a>
## Step 1: Project Setup

Create a new directory and set up your project:
```bash
# Create project directory
mkdir fastkit-quickstart
cd fastkit-quickstart

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install FastKit Core
pip install fastkit-core

# Create project structure
mkdir config
touch main.py models.py services.py config/database.py .env
```

Your structure should look like:
```
fastkit-quickstart/
├── venv/
├── config/
│   └── database.py
├── .env
├── main.py
├── models.py
└── services.py
```

---

<a name="step-2-configure-database"></a>
## Step 2: Configure Database

For this quickstart, we'll use SQLite (no installation needed!).

**Create `.env` file:**
```bash
# .env
DB_DRIVER=sqlite
DB_NAME=quickstart.db
```

**Create `config/database.py`:**
```python
# config/database.py
import os

CONNECTIONS = {
    'default': {
        'driver': os.getenv('DB_DRIVER', 'sqlite'),
        'database': os.getenv('DB_NAME', 'quickstart.db'),
        'echo': False  # Set to True to see SQL queries
    }
}
```
---

<a name="step-3-create-your-model"></a>
## Step 3: Create Your Model

**Create `models.py`:**
```python
# models.py
from fastkit_core.database import Base, IntIdMixin, TimestampMixin
from fastkit_core.validation import BaseSchema
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean

# Database Model
class Todo(Base, IntIdMixin, TimestampMixin):
    """Todo database model with auto ID and timestamps."""
    __tablename__ = 'todos'
    
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


# Validation Schemas
class TodoCreate(BaseSchema):
    """Schema for creating a todo."""
    title: str
    description: str | None = None


class TodoUpdate(BaseSchema):
    """Schema for updating a todo."""
    title: str | None = None
    description: str | None = None
    completed: bool | None = None


class TodoResponse(BaseSchema):
    """Schema for todo responses."""
    id: int
    title: str
    description: str | None
    completed: bool
    
    model_config = {"from_attributes": True}
```

**What's happening:**
- `IntIdMixin` - Adds auto-incrementing `id` field
- `TimestampMixin` - Adds `created_at` and `updated_at` timestamps
- Pydantic schemas - Handle validation and serialization

---

<a name="step-4-create-service"></a>
## Step 4: Create Service

**Create `services.py`:**
```python
# services.py
from fastkit_core.services import BaseCrudService
from fastkit_core.database import Repository
from models import Todo, TodoCreate, TodoUpdate
from sqlalchemy.orm import Session


class TodoService(BaseCrudService[Todo, TodoCreate, TodoUpdate]):
    """Service for Todo business logic."""
    
    def __init__(self, session: Session):
        repository = Repository(Todo, session)
        super().__init__(repository)
    
    def mark_completed(self, todo_id: int) -> Todo:
        """Mark a todo as completed."""
        return self.update(todo_id, {"completed": True})
    
    def mark_incomplete(self, todo_id: int) -> Todo:
        """Mark a todo as incomplete."""
        return self.update(todo_id, {"completed": False})
```

**What's happening:**
- `BaseCrudService` - Provides create, read, update, delete operations
- Custom methods - Add your own business logic
- Repository pattern - Handles database operations

---

<a name="step-5-create-api-endpoints"></a>
## Step 5: Create API Endpoints

**Create `main.py`:**
```python
# main.py
from fastapi import FastAPI, Depends
from fastkit_core.config import ConfigManager
from fastkit_core.database import init_database, get_db
from fastkit_core.http import success_response, paginated_response
from sqlalchemy.orm import Session
from models import Todo, TodoCreate, TodoUpdate, TodoResponse
from services import TodoService

# Initialize FastAPI
app = FastAPI(title="FastKit Quickstart API")

# Configure database
config = ConfigManager(modules=['database'], auto_load=True)
init_database(config)

# Create database tables
from fastkit_core.database import get_db_manager
Todo.metadata.create_all(get_db_manager().engine)


# Dependency injection
def get_todo_service(session: Session = Depends(get_db)) -> TodoService:
    return TodoService(session)


# API Endpoints
@app.post("/todos", status_code=201)
def create_todo(
    todo: TodoCreate,
    service: TodoService = Depends(get_todo_service)
):
    """Create a new todo."""
    created = service.create(todo.model_dump())
    return success_response(
        data=TodoResponse.model_validate(created).model_dump(),
        message="Todo created successfully"
    )


@app.get("/todos")
def list_todos(
    page: int = 1,
    per_page: int = 10,
    completed: bool | None = None,
    service: TodoService = Depends(get_todo_service)
):
    """List all todos with pagination."""
    filters = {}
    if completed is not None:
        filters["completed"] = completed
    
    todos, meta = service.paginate(
        page=page,
        per_page=per_page,
        **filters
    )
    return paginated_response(
        items=[TodoResponse.from_orm(t).model_dump() for t in todos],
        pagination=meta
    )


@app.get("/todos/{todo_id}")
def get_todo(
    todo_id: int,
    service: TodoService = Depends(get_todo_service)
):
    """Get a specific todo."""
    todo = service.find_or_fail(todo_id)
    return success_response(
        data=TodoResponse.model_validate(todo).model_dump()
    )


@app.put("/todos/{todo_id}")
def update_todo(
    todo_id: int,
    todo: TodoUpdate,
    service: TodoService = Depends(get_todo_service)
):
    """Update a todo."""
    updated = service.update(todo_id, todo.model_dump(exclude_unset=True))
    return success_response(
        data=TodoResponse.model_validate(updated).model_dump(),
        message="Todo updated successfully"
    )


@app.post("/todos/{todo_id}/complete")
def complete_todo(
    todo_id: int,
    service: TodoService = Depends(get_todo_service)
):
    """Mark todo as completed."""
    todo = service.mark_completed(todo_id)
    return success_response(
        data=TodoResponse.model_validate(todo).model_dump(),
        message="Todo marked as completed"
    )


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(
    todo_id: int,
    service: TodoService = Depends(get_todo_service)
):
    """Delete a todo."""
    service.delete(todo_id)


@app.get("/")
def root():
    """API root endpoint."""
    return {
        "message": "Welcome to FastKit Quickstart API!",
        "docs": "/docs"
    }
```

---

<a name="step-6-run-your-api"></a>
## Step 6: Run Your API

Start your API server:
```bash
uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

🎉 **Your API is running!** Visit http://127.0.0.1:8000/docs

---

<a name="test-your-api"></a>
## Test Your API

### Using the Interactive Docs

1. Open http://127.0.0.1:8000/docs in your browser
2. Try the "POST /todos" endpoint
3. Create a todo with:
```json
   {
     "title": "Learn FastKit Core",
     "description": "Complete the quickstart guide"
   }
```

### Using curl
```bash
# Create a todo
curl -X POST http://127.0.0.1:8000/todos \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn FastKit Core",
    "description": "Complete the quickstart guide"
  }'

# List todos
curl http://127.0.0.1:8000/todos

# Get specific todo
curl http://127.0.0.1:8000/todos/1

# Mark as completed
curl -X POST http://127.0.0.1:8000/todos/1/complete

# Update todo
curl -X PUT http://127.0.0.1:8000/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Master FastKit Core"}'

# Delete todo
curl -X DELETE http://127.0.0.1:8000/todos/1
```

### Using Python requests
```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# Create a todo
response = requests.post(
    f"{BASE_URL}/todos",
    json={
        "title": "Learn FastKit Core",
        "description": "Complete the quickstart guide"
    }
)
print(response.json())

# List todos
response = requests.get(f"{BASE_URL}/todos")
print(response.json())
```

---

<a name="what-you-built"></a>
## What You Built

🎉 **Congratulations!** In just a few minutes, you created a production-ready API with:

**Database Operations**
- SQLAlchemy models with mixins
- Automatic ID and timestamp management
- Repository pattern for data access

**Business Logic Layer**
- Service class with CRUD operations
- Custom business methods (`mark_completed`, `mark_incomplete`)
- Reusable across endpoints, CLI, tasks, tests

**API Endpoints**
- Create, read, update, delete operations
- Pagination with metadata
- Filtering by completion status
- Custom action endpoints

**Validation**
- Pydantic schemas for request validation
- Type-safe data handling
- Automatic error messages

**Standardized Responses**
- Consistent API format
- Success/error handling
- Pagination metadata

---

<a name="next-steps"></a>
## Next Steps

Now that you've built your first API, explore FastKit Core's features:

### Learn Core Concepts

**[Database Guide →](/docs/database)**
- Multiple database connections
- Advanced filtering with Django-style operators
- Soft deletes and complex queries
- Read replicas for scaling

**[Services →](/docs/services)**
- Lifecycle hooks (before_create, after_update)
- Complex business logic patterns
- Service composition

**[Validation →](/docs/validation)**
- Custom validation rules
- Translated error messages
- Complex validation scenarios

**[HTTP Utilities →](/docs/http)**
- Custom exception handling
- Middleware patterns
- Response formatters

### Add Features


**Multi-language Support**
```python
# Use TranslatableMixin for multi-language content
from fastkit_core.database import TranslatableMixin

class Todo(Base, IntIdMixin, TimestampMixin, TranslatableMixin):
    __translatable_fields__ = ['title', 'description']
```

---

## Troubleshooting

### Import Errors

If you get import errors, make sure FastKit Core is installed:
```bash
pip install --upgrade fastkit-core
```

### Database Connection Issues

For SQLite, no configuration needed! For other databases:
```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install pymysql
```

### Port Already in Use

If port 8000 is in use, try a different port:
```bash
uvicorn main:app --reload --port 8001
```

---

## Full Source Code

The complete quickstart code is available on GitHub:

[Download Quickstart Code](https://github.com/codevelo-pub/fastkit-examples/quickstart)

---

## Need Help?

-  [Full Documentation](/docs)
-  [GitHub Discussions](https://github.com/codevelo-pub/fastkit-core/discussions)
-  [Report Issues](https://github.com/codevelo-pub/fastkit-core/issues)
-  [Star on GitHub](https://github.com/codevelo-pub/fastkit-core)

---

**Happy coding with FastKit Core! 🚀**