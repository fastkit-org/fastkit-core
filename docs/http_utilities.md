# HTTP Utilities

- [Introduction](#introduction)
- [Quick Example](#quick-example)
- [Response Formatters](#response-formatters)
- [Exceptions](#exceptions)
- [Exception Handlers](#exception-handlers)
- [Middleware](#middleware)
- [Dependencies](#dependencies)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's HTTP module provides standardized response formats, custom exceptions, 
middleware, and helper functions for building consistent and maintainable APIs.

**Key Features:**

-  **Standardized Responses** - Consistent JSON format across your API
-  **Custom Exceptions** - Type-safe error handling
-  **Automatic Error Handling** - Global exception handlers
-  **Middleware** - Request ID, locale detection, and more
-  **Helper Dependencies** - Pagination, locale, and common patterns
-  **Translated Errors** - Multi-language error messages
-  **Type-safe** - Full type checking support

---

<a name="quick-example"></a>
## Quick Example

**Setup your FastAPI application:**
```python
from fastapi import FastAPI
from fastkit_core.http import (
    register_exception_handlers,
    RequestIDMiddleware,
    LocaleMiddleware
)

app = FastAPI()

# Register exception handlers
register_exception_handlers(app)

# Add middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LocaleMiddleware)
```

**Use standardized responses:**
```python
from fastapi import FastAPI, Depends
from fastkit_core.http import (
    success_response,
    error_response,
    paginated_response,
    NotFoundException,
    get_pagination
)

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = database.get_user(user_id)
    
    if not user:
        raise NotFoundException("User not found")
    
    return success_response(
        data={"id": user.id, "name": user.name},
        message="User retrieved successfully"
    )

@app.get("/users")
def list_users(pagination: dict = Depends(get_pagination)):
    users, meta = service.paginate(**pagination)
    
    return paginated_response(
        items=[u.to_dict() for u in users],
        pagination=meta
    )
```

**Response format:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Alice"
  },
  "message": "User retrieved successfully"
}
```

---

<a name="response-formatters"></a>
## Response Formatters

### Success Response

Standard format for successful operations:
```python
from fastkit_core.http import success_response

@app.post("/products")
def create_product(product: ProductCreate):
    created = service.create(product.model_dump())
    
    return success_response(
        data={"id": created.id, "name": created.name},
        message="Product created successfully",
        status_code=201
    )
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Product Name"
  },
  "message": "Product created successfully"
}
```

**Parameters:**
- `data` (Any, optional) - Response data
- `message` (str, optional) - Success message
- `status_code` (int, default=200) - HTTP status code

### Error Response

Standard format for error responses:
```python
from fastkit_core.http import error_response

@app.post("/users")
def create_user(data: dict):
    if not data.get('email'):
        return error_response(
            message="Validation failed",
            errors={"email": ["Email is required"]},
            status_code=422
        )
    
    # Create user...
```

**Response:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "email": ["Email is required"]
  }
}
```

**Parameters:**
- `message` (str, required) - Error message
- `errors` (dict, optional) - Detailed errors (e.g., validation errors)
- `status_code` (int, default=400) - HTTP status code

### Paginated Response

Standard format for paginated lists:
```python
from fastapi import Depends
from fastkit_core.http import paginated_response, get_pagination

@app.get("/products")
def list_products(pagination: dict = Depends(get_pagination)):
    products, meta = service.paginate(
        page=pagination['page'],
        per_page=pagination['per_page']
    )
    
    return paginated_response(
        items=[p.to_dict() for p in products],
        pagination=meta,
        message="Products retrieved successfully"
    )
```

**Response:**
```json
{
  "success": true,
  "data": [
    {"id": 1, "name": "Product 1"},
    {"id": 2, "name": "Product 2"}
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  },
  "message": "Products retrieved successfully"
}
```

**Parameters:**
- `items` (list, required) - List of items
- `pagination` (dict, required) - Pagination metadata from repository
- `message` (str, optional) - Optional message
- `status_code` (int, default=200) - HTTP status code

---

<a name="exceptions"></a>
## Exceptions

FastKit Core provides custom exceptions for common HTTP errors.

### Base Exception

All FastKit exceptions inherit from `FastKitException`:
```python
from fastkit_core.http import FastKitException

class CustomException(FastKitException):
    """Custom application exception."""
    def __init__(self, message: str = "Custom error"):
        super().__init__(message, status_code=418)

# Usage
raise CustomException("Something went wrong")
```

### NotFoundException (404)

For missing resources:
```python
from fastkit_core.http import NotFoundException

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = database.get_user(user_id)
    
    if not user:
        raise NotFoundException("User not found")
    
    return success_response(data=user.to_dict())
```

**Default message:** "Resource not found"  
**Status code:** 404

### ValidationException (422)

For validation errors:
```python
from fastkit_core.http import ValidationException

@app.post("/users")
def create_user(data: dict):
    errors = validate_user_data(data)
    
    if errors:
        raise ValidationException(
            errors=errors,
            message="Validation failed"
        )
    
    # Create user...
```

**Default message:** "Validation failed"  
**Status code:** 422

### UnauthorizedException (401)

For authentication failures:
```python
from fastkit_core.http import UnauthorizedException

@app.get("/profile")
def get_profile(token: str):
    user = verify_token(token)
    
    if not user:
        raise UnauthorizedException("Invalid or expired token")
    
    return success_response(data=user.to_dict())
```

**Default message:** "Unauthorized"  
**Status code:** 401

### ForbiddenException (403)

For authorization failures:
```python
from fastkit_core.http import ForbiddenException

@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: User):
    if not current_user.is_admin:
        raise ForbiddenException("Only admins can delete users")
    
    # Delete user...
```

**Default message:** "Forbidden"  
**Status code:** 403

### Exception with Details

Include error details in any exception:
```python
from fastkit_core.http import FastKitException

raise FastKitException(
    message="Operation failed",
    status_code=400,
    errors={
        "field1": ["Error 1", "Error 2"],
        "field2": ["Error 3"]
    }
)
```

---

<a name="exception-handlers"></a>
## Exception Handlers

Register global exception handlers to automatically format all errors.

### Setup

Call `register_exception_handlers()` once when creating your app:
```python
from fastapi import FastAPI
from fastkit_core.http import register_exception_handlers

app = FastAPI()

# Register all exception handlers
register_exception_handlers(app)
```

### What It Handles

**1. FastKit Exceptions**

Automatically formats all `FastKitException` errors:
```python
from fastkit_core.http import NotFoundException

@app.get("/users/{user_id}")
def get_user(user_id: int):
    raise NotFoundException("User not found")
    # Returns: {"success": false, "message": "User not found"}
```

**2. FastAPI Validation Errors**

Automatically formats FastAPI's `RequestValidationError`:
```python
@app.post("/users")
def create_user(user: UserCreate):
    # If validation fails, automatically returns:
    # {
    #   "success": false,
    #   "message": "Validation failed",
    #   "errors": {"field": ["error message"]}
    # }
    pass
```

**3. Pydantic Validation Errors**

Formats Pydantic's `ValidationError` with translations:
```python
from pydantic import ValidationError

@app.post("/users")
def create_user(data: dict):
    try:
        user = UserCreate(**data)
    except ValidationError as e:
        # Automatically formatted with translations
        # Returns formatted error response
        pass
```

**4. Unexpected Exceptions**

Catches all unexpected exceptions:
```python
@app.get("/error")
def error_endpoint():
    raise ValueError("Something went wrong")
    # Development: Returns detailed error
    # Production: Returns "Internal server error"
```

### Debug Mode

Exception details are shown based on `DEBUG` setting:
```python
# config/app.py
DEBUG = True  # Show detailed errors

DEBUG = False  # Hide details in production
```

**Development (DEBUG=True):**
```json
{
  "success": false,
  "message": "division by zero"
}
```

**Production (DEBUG=False):**
```json
{
  "success": false,
  "message": "Internal server error"
}
```

---

<a name="middleware"></a>
## Middleware

### RequestIDMiddleware

Adds unique request ID to each request for tracking and logging.

**Setup:**
```python
from fastapi import FastAPI
from fastkit_core.http import RequestIDMiddleware

app = FastAPI()
app.add_middleware(RequestIDMiddleware)
```

**Features:**
- Generates unique UUID for each request
- Available in routes via `request.state.request_id`
- Added to response headers as `X-Request-ID`

**Usage in routes:**
```python
from fastapi import Request

@app.get("/")
def root(request: Request):
    request_id = request.state.request_id
    
    # Use for logging
    logger.info(f"Request {request_id}: Processing")
    
    return {"request_id": request_id}
```

**Response headers:**
```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Benefits:**
-  Track requests across services
-  Correlate logs
-  Debug distributed systems
-  Customer support (users can provide request ID)

### LocaleMiddleware

Automatically detects and sets user locale from various sources.

**Setup:**
```python
from fastapi import FastAPI
from fastkit_core.http import LocaleMiddleware

app = FastAPI()
app.add_middleware(LocaleMiddleware)
```

**Detection Priority:**

1. **Accept-Language header** (first 2 chars)
2. **?lang= query parameter**
3. **locale cookie**
4. **Default: 'en'**

**Examples:**
```bash
# From header
curl http://localhost:8000/api \
  -H "Accept-Language: es-ES,es;q=0.9"
# Sets locale to 'es'

# From query parameter
curl http://localhost:8000/api?lang=fr
# Sets locale to 'fr'

# From cookie
curl http://localhost:8000/api \
  --cookie "locale=de"
# Sets locale to 'de'
```

**Usage in routes:**
```python
from fastkit_core.i18n import get_locale, _

@app.get("/")
def root():
    current_locale = get_locale()
    message = _('messages.welcome')
    
    return {
        "locale": current_locale,
        "message": message
    }
```

### Combining Middleware

Use multiple middleware together:
```python
from fastapi import FastAPI
from fastkit_core.http import RequestIDMiddleware, LocaleMiddleware

app = FastAPI()

# Order matters: first added = outer layer
app.add_middleware(LocaleMiddleware)      # Runs second
app.add_middleware(RequestIDMiddleware)   # Runs first
```

### Custom Middleware

Create your own middleware following the same pattern:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class TimingMiddleware(BaseHTTPMiddleware):
    """Add request timing information."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        import time
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers['X-Process-Time'] = str(process_time)
        return response

# Register
app.add_middleware(TimingMiddleware)
```

---

<a name="dependencies"></a>
## Dependencies

FastKit Core provides reusable FastAPI dependencies.

### Pagination Dependency

Extract and validate pagination parameters:
```python
from fastapi import Depends
from fastkit_core.http import get_pagination

@app.get("/products")
def list_products(pagination: dict = Depends(get_pagination)):
    # pagination = {
    #     'page': 1,
    #     'per_page': 20,
    #     'offset': 0
    # }
    
    products, meta = service.paginate(
        page=pagination['page'],
        per_page=pagination['per_page']
    )
    
    return paginated_response(items=products, pagination=meta)
```

**Query parameters:**
- `page` (int, default=1, min=1) - Page number
- `per_page` (int, default=20, min=1, max=100) - Items per page

**Request:**
```bash
curl "http://localhost:8000/products?page=2&per_page=50"
```

**Returns:**
```python
{
    'page': 2,
    'per_page': 50,
    'offset': 50
}
```

### Locale Dependency

Get locale from query parameter or context:
```python
from fastapi import Depends
from fastkit_core.http import get_locale as get_locale_dep
from fastkit_core.i18n import _

@app.get("/greeting")
def greeting(locale: str = Depends(get_locale_dep)):
    return {
        "locale": locale,
        "message": _('messages.hello')
    }
```

**Request:**
```bash
# From query parameter
curl "http://localhost:8000/greeting?locale=es"

# From context (set by LocaleMiddleware)
curl "http://localhost:8000/greeting" \
  -H "Accept-Language: fr"
```

### Custom Dependencies

Create your own reusable dependencies:
```python
from fastapi import Depends, Header, HTTPException
from typing import Annotated

async def get_current_user(
    authorization: Annotated[str, Header()]
) -> User:
    """Extract and validate user from authorization header."""
    token = authorization.replace("Bearer ", "")
    user = verify_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return user

# Usage
@app.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {"user": current_user.to_dict()}
```

---

<a name="best-practices"></a>
## Best Practices

### 1. Always Use Response Formatters

✅ **Good:**
```python
from fastkit_core.http import success_response

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = service.get(user_id)
    return success_response(data=user.to_dict())
```

❌ **Bad:**
```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = service.get(user_id)
    return {"user": user.to_dict()}  # Inconsistent format
```

### 2. Use Exceptions Instead of Returns

✅ **Good:**
```python
from fastkit_core.http import NotFoundException

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = service.get(user_id)
    if not user:
        raise NotFoundException("User not found")
    return success_response(data=user.to_dict())
```

❌ **Bad:**
```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = service.get(user_id)
    if not user:
        return {"error": "Not found"}, 404  # Inconsistent
    return {"user": user.to_dict()}
```

### 3. Register Exception Handlers Early
```python
from fastapi import FastAPI
from fastkit_core.http import register_exception_handlers

app = FastAPI()

# Register BEFORE defining routes
register_exception_handlers(app)

@app.get("/")
def root():
    ...
```

### 4. Use Middleware for Cross-Cutting Concerns

✅ **Good:**
```python
# Use middleware for locale detection
app.add_middleware(LocaleMiddleware)

@app.get("/")
def root():
    # Locale already set by middleware
    message = _('messages.welcome')
    return {"message": message}
```

❌ **Bad:**
```python
# Manual locale detection in every route
@app.get("/")
def root(accept_language: str = Header(default='en')):
    locale = accept_language[:2]
    set_locale(locale)
    message = _('messages.welcome')
    return {"message": message}
```

### 5. Include Messages with Data
```python
from fastkit_core.http import success_response

@app.post("/users")
def create_user(user: UserCreate):
    created = service.create(user.model_dump())
    
    return success_response(
        data={"id": created.id},
        message="User created successfully",  # Include message
        status_code=201
    )
```

### 6. Use Type Hints
```python
from fastkit_core.http import NotFoundException
from models import User

@app.get("/users/{user_id}")
def get_user(user_id: int) -> User:  # Type hint
    user = service.get(user_id)
    if not user:
        raise NotFoundException()
    return user
```

### 7. Structure Error Responses
```python
from fastkit_core.http import ValidationException

@app.post("/users")
def create_user(data: dict):
    errors = {}
    
    if not data.get('email'):
        errors['email'] = ["Email is required"]
    
    if not data.get('password'):
        errors['password'] = ["Password is required"]
    
    if errors:
        raise ValidationException(errors=errors)
    
    # Continue...
```

---

<a name="api-reference"></a>
## API Reference

### Response Formatters

**`success_response(data=None, message=None, status_code=200)`**

Standard success response.
```python
return success_response(
    data={"id": 1, "name": "Product"},
    message="Product created",
    status_code=201
)
```

**`error_response(message, errors=None, status_code=400)`**

Standard error response.
```python
return error_response(
    message="Validation failed",
    errors={"email": ["Invalid email"]},
    status_code=422
)
```

**`paginated_response(items, pagination, message=None, status_code=200)`**

Paginated response with metadata.
```python
return paginated_response(
    items=[...],
    pagination={
        'page': 1,
        'per_page': 20,
        'total': 100,
        'total_pages': 5,
        'has_next': True,
        'has_prev': False
    }
)
```

---

### Exceptions

**`FastKitException(message, status_code=400, errors=None)`**

Base exception for all FastKit errors.
```python
raise FastKitException(
    message="Something went wrong",
    status_code=500,
    errors={"detail": "Error details"}
)
```

**`NotFoundException(message="Resource not found")`**

404 Not Found exception.
```python
raise NotFoundException("User not found")
```

**`ValidationException(errors, message="Validation failed")`**

422 Unprocessable Entity exception.
```python
raise ValidationException(
    errors={"email": ["Invalid email"]},
    message="Validation failed"
)
```

**`UnauthorizedException(message="Unauthorized")`**

401 Unauthorized exception.
```python
raise UnauthorizedException("Invalid token")
```

**`ForbiddenException(message="Forbidden")`**

403 Forbidden exception.
```python
raise ForbiddenException("Admin access required")
```

---

### Middleware

**`RequestIDMiddleware`**

Adds unique request ID to each request.
```python
app.add_middleware(RequestIDMiddleware)

# Access in routes
@app.get("/")
def root(request: Request):
    request_id = request.state.request_id
    return {"request_id": request_id}
```

**`LocaleMiddleware`**

Detects and sets user locale.
```python
app.add_middleware(LocaleMiddleware)

# Locale automatically set from:
# 1. Accept-Language header
# 2. ?lang= query parameter
# 3. locale cookie
# 4. Default: 'en'
```

---

### Dependencies

**`get_pagination(page=1, per_page=20)`**

Extract pagination parameters.
```python
@app.get("/items")
def list_items(pagination: dict = Depends(get_pagination)):
    # pagination = {'page': 1, 'per_page': 20, 'offset': 0}
    ...
```

**`get_locale(locale=None)`**

Get locale from query parameter or context.
```python
@app.get("/")
def root(locale: str = Depends(get_locale)):
    # locale = current locale
    ...
```

---

### Exception Handler

**`register_exception_handlers(app)`**

Register all exception handlers.
```python
from fastapi import FastAPI
from fastkit_core.http import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

---

## Complete Example
```python
from fastapi import FastAPI, Depends
from fastkit_core.http import (
    success_response,
    error_response,
    paginated_response,
    NotFoundException,
    ValidationException,
    register_exception_handlers,
    RequestIDMiddleware,
    LocaleMiddleware,
    get_pagination
)
from fastkit_core.i18n import _

# Create app
app = FastAPI()

# Register exception handlers
register_exception_handlers(app)

# Add middleware
app.add_middleware(LocaleMiddleware)
app.add_middleware(RequestIDMiddleware)

# Routes
@app.get("/")
def root():
    return success_response(
        data={"version": "1.0.0"},
        message=_('messages.welcome')
    )

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = database.get_user(user_id)
    
    if not user:
        raise NotFoundException(_('errors.user_not_found'))
    
    return success_response(data=user.to_dict())

@app.get("/users")
def list_users(pagination: dict = Depends(get_pagination)):
    users, meta = service.paginate(**pagination)
    
    return paginated_response(
        items=[u.to_dict() for u in users],
        pagination=meta
    )

@app.post("/users")
def create_user(data: dict):
    errors = validate_user(data)
    
    if errors:
        raise ValidationException(
            errors=errors,
            message=_('validation.failed')
        )
    
    user = service.create(data)
    
    return success_response(
        data={"id": user.id},
        message=_('messages.user_created'),
        status_code=201
    )
```

---

## Next Steps

Now that you understand HTTP utilities, explore:

- **[Validation](/docs/validation)** - Works seamlessly with HTTP exceptions
- **[Services](/docs/services)** - Use HTTP responses in service layer
- **[Translations](/docs/translations)** - Translate error messages
