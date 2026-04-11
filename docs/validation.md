# Validation

- [Introduction](#introduction)
- [Quick Example](#quick-example)
- [BaseSchema](#baseschema)
- [BaseCreateSchema](#basecreataschema)
- [BaseUpdateSchema](#baseupdateschema)
- [Computed Fields](#computed-fields)
- [Serialization Helpers](#serialization-helpers)
- [Validation Rules](#validation-rules)
- [Validator Mixins](#validator-mixins)
- [Translated Error Messages](#translated-error-messages)
- [API Integration](#api-integration)
- [Custom Validators](#custom-validators)
- [Error Helpers](#error-helpers)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's validation system is built on top of Pydantic v2, adding automatic
translation of error messages, reusable validator mixins, and convenient validation rules.

**Key Features:**

- **ORM-ready by default** — `from_attributes=True` on every schema, no extra config needed
- **Create / Update conventions** — `BaseCreateSchema` and `BaseUpdateSchema` with sensible defaults
- **Computed fields** — `@computed_field` pattern fully supported and documented
- **Serialization helpers** — `to_dict()` and `to_json_str()` with `exclude_none` support
- **Translated Errors** — Automatic translation of validation messages
- **Reusable Mixins** — Common validators (password, username, slug)
- **Simple Rules** — Helper functions for common validations
- **Structured Errors** — Clean error format for APIs
- **Multi-language** — Error messages in user's language

---

<a name="quick-example"></a>
## Quick Example

```python
from fastkit_core.validation import BaseCreateSchema, PasswordValidatorMixin
from pydantic import EmailStr

class UserCreate(BaseCreateSchema, PasswordValidatorMixin):
    """User registration schema — extra fields forbidden, ORM-ready."""
    username: str
    email: EmailStr
    password: str  # Validated by PasswordValidatorMixin
```

```python
from fastapi import FastAPI
from fastkit_core.http import error_response
from pydantic import ValidationError

app = FastAPI()

@app.post("/users")
def create_user(user: UserCreate):
    # FastAPI validates automatically — returns 422 if validation fails
    return {"message": "User created"}
```

**Error response:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "username": ["The username must be at least 3 characters"],
    "password": [
      "Password must be at least 8 characters",
      "Password must contain at least one uppercase letter"
    ]
  }
}
```

---

<a name="baseschema"></a>
## BaseSchema

`BaseSchema` is the foundation of all FastKit schemas. It extends Pydantic's `BaseModel` with:

- `from_attributes=True` enabled by default — works directly with SQLAlchemy ORM objects
- Standardized error formatting with i18n support
- `to_dict()` and `to_json_str()` serialization helpers
- `config_exclude_none()` and `config_exclude_fields()` config helpers

### ORM Mode by Default

Every schema that extends `BaseSchema` can be built from an SQLAlchemy ORM object
without any extra configuration:

```python
from fastkit_core.validation import BaseSchema

class UserResponse(BaseSchema):
    id: int
    name: str
    email: str
    # from_attributes=True is already set — no model_config needed

# Works directly with ORM instances
user_response = UserResponse.model_validate(user_orm_instance)

# Also works with plain dicts
user_response = UserResponse.model_validate({"id": 1, "name": "Alice", "email": "a@x.com"})
```

Previously you had to remember to add `model_config = ConfigDict(from_attributes=True)` on
every response schema. With `BaseSchema` this is handled once for all subclasses.

### Error Formatting

```python
from pydantic import ValidationError

try:
    product = ProductCreate(name="", price=-10)
except ValidationError as e:
    errors = ProductCreate.format_errors(e)
    # {'name': ['String should have at least 1 character'], 'price': ['...']}
```

### Validation Message Mapping

`BaseSchema` maps Pydantic error types to i18n translation keys:

```python
VALIDATION_MESSAGE_MAP = {
    'missing': 'validation.required',
    'string_too_short': 'validation.string_too_short',
    'string_too_long': 'validation.string_too_long',
    'value_error': 'validation.value_error',
    'value_error.email': 'validation.email',
    'value_error.url': 'validation.url',
    'greater_than_equal': 'validation.greater_than_equal',
    'less_than_equal': 'validation.less_than_equal',
    'greater_than': 'validation.greater_than',
    'less_than': 'validation.less_than',
    'string_pattern_mismatch': 'validation.string_pattern_mismatch',
}
```

Create corresponding keys in `translations/en.json`:

```json
{
  "validation": {
    "required": "The {field} field is required",
    "string_too_short": "The {field} must be at least {min_length} characters",
    "string_too_long": "The {field} must not exceed {max_length} characters",
    "email": "The {field} must be a valid email address",
    "greater_than_equal": "The {field} must be at least {ge}",
    "less_than_equal": "The {field} must not exceed {le}"
  }
}
```

---

<a name="basecreataschema"></a>
## BaseCreateSchema

`BaseCreateSchema` extends `BaseSchema` with sensible defaults for **create operations**:

- Extra fields are **forbidden** — prevents accidental mass assignment
- Inherits `from_attributes=True` from `BaseSchema`

```python
from fastkit_core.validation import BaseCreateSchema

class UserCreate(BaseCreateSchema):
    name: str
    email: str
    role: str = "user"

# Valid
user = UserCreate(name="John", email="j@example.com")

# Extra field — raises ValidationError
UserCreate(name="John", email="j@example.com", is_admin=True)
# ValidationError: extra fields not permitted
```

Use `BaseCreateSchema` instead of `BaseSchema` for all input schemas that represent
creation of a new resource. The `extra='forbid'` behavior protects against
unintentional data injection even when the schema is used directly with `**request.dict()`.

---

<a name="baseupdateschema"></a>
## BaseUpdateSchema

`BaseUpdateSchema` extends `BaseSchema` with sensible defaults for **partial update operations**:

- Extra fields are **forbidden**
- All fields should be declared as `Optional` with `None` as default (by convention)
- Inherits `from_attributes=True` from `BaseSchema`

```python
from fastkit_core.validation import BaseUpdateSchema

class UserUpdate(BaseUpdateSchema):
    name: str | None = None
    email: str | None = None
    age: int | None = None
```

### Partial Update Pattern

Declaring fields as `Optional` with `None` default integrates cleanly with
`model_dump(exclude_unset=True)`, which is what `BaseCrudService._to_dict()` uses
internally. This means only the fields the caller explicitly set will be forwarded
to the repository:

```python
update = UserUpdate(name="Jane")

# Only the field that was explicitly set
update.model_dump(exclude_unset=True)
# {'name': 'Jane'}   ← email and age are not included

# Setting a field to None explicitly (to clear it)
update = UserUpdate(bio=None)
update.model_dump(exclude_unset=True)
# {'bio': None}   ← explicitly cleared
```

### Typical CRUD Schema Set

```python
from fastkit_core.validation import BaseCreateSchema, BaseUpdateSchema, BaseSchema
from pydantic import computed_field
from datetime import datetime

class UserCreate(BaseCreateSchema):
    name: str
    email: str
    role: str = "user"

class UserUpdate(BaseUpdateSchema):
    name: str | None = None
    email: str | None = None

class UserResponse(BaseSchema):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    updated_at: datetime
    # from_attributes=True already set — no extra config needed
```

---

<a name="computed-fields"></a>
## Computed Fields

Pydantic v2's `@computed_field` works out of the box on any `BaseSchema` subclass.
Use it to add derived, read-only properties to response schemas.

### Basic Usage

```python
from fastkit_core.validation import BaseSchema
from pydantic import computed_field

class UserResponse(BaseSchema):
    first_name: str
    last_name: str
    avatar_path: str | None = None

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        if not self.avatar_path:
            return None
        return f"/storage/{self.avatar_path}"

user = UserResponse(first_name="Jane", last_name="Doe", avatar_path="photo.jpg")

print(user.full_name)    # "Jane Doe"
print(user.avatar_url)   # "/storage/photo.jpg"
```

### Computed Fields in Serialization

Computed fields are automatically included in `to_dict()` and `to_json_str()`:

```python
data = user.to_dict()
# {
#   'first_name': 'Jane',
#   'last_name': 'Doe',
#   'avatar_path': 'photo.jpg',
#   'full_name': 'Jane Doe',
#   'avatar_url': '/storage/photo.jpg'
# }
```

### With ORM Objects

Computed fields work when the schema is built from an ORM object using `model_validate()`:

```python
# ORM instance
user_orm = session.get(User, 1)

# Computed fields are evaluated after the ORM data is loaded
user_response = UserResponse.model_validate(user_orm)
print(user_response.full_name)  # works
```

### Business Logic in Computed Fields

```python
class InvoiceResponse(BaseSchema):
    subtotal: float
    tax_rate: float = 0.20

    @computed_field
    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * self.tax_rate, 2)

    @computed_field
    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)
```

---

<a name="serialization-helpers"></a>
## Serialization Helpers

### to_dict()

Convert a schema instance to a plain Python dictionary:

```python
user = UserResponse(id=1, name="Alice", bio=None)

# Include all fields (default)
user.to_dict()
# {'id': 1, 'name': 'Alice', 'bio': None}

# Exclude None values
user.to_dict(exclude_none=True)
# {'id': 1, 'name': 'Alice'}
```

### to_json_str()

Serialize directly to a JSON string:

```python
user = UserResponse(id=1, name="Alice", bio=None)

user.to_json_str()
# '{"id":1,"name":"Alice","bio":null}'

user.to_json_str(exclude_none=True)
# '{"id":1,"name":"Alice"}'
```

### Config Helpers

Use these class methods when you want a schema to always serialize without None values
or always exclude specific fields:

```python
from fastkit_core.validation import BaseSchema
from pydantic import Field

# Always omit None values from serialization output
class UserResponse(BaseSchema):
    id: int
    name: str
    bio: str | None = None

    model_config = BaseSchema.config_exclude_none()

UserResponse(id=1, name="Alice", bio=None).model_dump()
# {'id': 1, 'name': 'Alice'}

# Exclude a specific field from all serialization
class UserResponse(BaseSchema):
    id: int
    name: str
    internal_token: str = Field(exclude=True)

    model_config = BaseSchema.config_exclude_fields(['internal_token'])

UserResponse(id=1, name="Alice", internal_token="secret").to_dict()
# {'id': 1, 'name': 'Alice'}
```

---

<a name="validation-rules"></a>
## Validation Rules

FastKit Core provides convenient helper functions for common validation rules.
These are simple wrappers around `pydantic.Field()`.

### String Length

```python
from fastkit_core.validation import BaseCreateSchema, min_length, max_length, length

class PostCreate(BaseCreateSchema):
    title: str = min_length(5)        # At least 5 characters
    slug: str = max_length(100)       # At most 100 characters
    excerpt: str = length(10, 200)    # Between 10 and 200 characters
```

### Numeric Ranges

```python
from fastkit_core.validation import BaseCreateSchema, min_value, max_value, between

class ProductCreate(BaseCreateSchema):
    price: float = min_value(0.01)      # At least 0.01
    stock: int = max_value(1000)        # At most 1000
    rating: float = between(1.0, 5.0)  # Between 1.0 and 5.0
```

### Pattern Matching

```python
from fastkit_core.validation import BaseCreateSchema, pattern

class CodeCreate(BaseCreateSchema):
    hex_color: str = pattern(r'^#[0-9A-Fa-f]{6}$')
    phone: str = pattern(r'^\+?1?\d{9,15}$')
```

### Combining Rules

```python
from pydantic import Field
from fastkit_core.validation import BaseCreateSchema, length

class UserCreate(BaseCreateSchema):
    username: str = Field(min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    bio: str = length(10, 500)
```

---

<a name="validator-mixins"></a>
## Validator Mixins

Reusable mixins for common validation patterns. Combine them with any schema class.

### PasswordValidatorMixin

Standard password validation (8–16 chars, uppercase, special character):

```python
from fastkit_core.validation import BaseCreateSchema, PasswordValidatorMixin

class UserCreate(BaseCreateSchema, PasswordValidatorMixin):
    username: str
    email: str
    password: str  # Validated automatically

# Requirements: 8–16 chars, ≥1 uppercase, ≥1 special character
```

**Customize:**

```python
class CustomPasswordSchema(BaseCreateSchema, PasswordValidatorMixin):
    PWD_MIN_LENGTH = 10  # Override minimum length
    PWD_MAX_LENGTH = 30  # Override maximum length

    password: str
```

### StrongPasswordValidatorMixin

Strong password validation (10–20 chars, all character classes):

```python
from fastkit_core.validation import BaseCreateSchema, StrongPasswordValidatorMixin

class AdminCreate(BaseCreateSchema, StrongPasswordValidatorMixin):
    username: str
    password: str

# Requirements: 10–20 chars, ≥1 uppercase, ≥1 lowercase, ≥1 digit, ≥1 special char
```

### UsernameValidatorMixin

Username validation (3–20 chars, alphanumeric + underscore, cannot start with digit):

```python
from fastkit_core.validation import BaseCreateSchema, UsernameValidatorMixin

class UserCreate(BaseCreateSchema, UsernameValidatorMixin):
    username: str
    email: str
```

**Customize:**

```python
class UserCreate(BaseCreateSchema, UsernameValidatorMixin):
    USM_MIN_LENGTH = 5
    USM_MAX_LENGTH = 15
    username: str
```

### SlugValidatorMixin

URL-friendly slug validation:

```python
from fastkit_core.validation import BaseCreateSchema, SlugValidatorMixin

class PostCreate(BaseCreateSchema, SlugValidatorMixin):
    title: str
    slug: str

# Valid:   hello-world, fastkit-core-2024, my-awesome-post
# Invalid: Hello-World (uppercase), hello--world (consecutive hyphens), -hello (leading hyphen)
```

### Combining Multiple Mixins

```python
from fastkit_core.validation import (
    BaseCreateSchema,
    UsernameValidatorMixin,
    PasswordValidatorMixin,
    SlugValidatorMixin,
)

class UserCreate(BaseCreateSchema, UsernameValidatorMixin, PasswordValidatorMixin):
    username: str
    password: str
    email: str
```

---

<a name="translated-error-messages"></a>
## Translated Error Messages

All validation errors are automatically translated based on the current locale.

### Translation File Structure

```json
// translations/en.json
{
  "validation": {
    "required": "The {field} field is required",
    "string_too_short": "The {field} must be at least {min_length} characters",
    "string_too_long": "The {field} must not exceed {max_length} characters",
    "email": "The {field} must be a valid email address",
    "greater_than_equal": "The {field} must be at least {ge}",
    "password": {
      "min_length": "Password must be at least {min} characters",
      "max_length": "Password must not exceed {max} characters",
      "uppercase": "Password must contain at least one uppercase letter",
      "lowercase": "Password must contain at least one lowercase letter",
      "digit": "Password must contain at least one digit",
      "special_char": "Password must contain at least one special character"
    },
    "username": {
      "min_length": "Username must be at least {min} characters",
      "max_length": "Username must not exceed {max} characters",
      "format": "Username must start with a letter and contain only letters, numbers, and underscores"
    },
    "slug": {
      "format": "Slug must be lowercase letters, numbers, and hyphens only"
    }
  }
}
```

### Locale Middleware

```python
from fastapi import FastAPI, Request
from fastkit_core.i18n import set_locale

app = FastAPI()

@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    locale = request.headers.get('Accept-Language', 'en')[:2]
    set_locale(locale)
    return await call_next(request)
```

---

<a name="api-integration"></a>
## API Integration

### FastAPI Automatic Validation

```python
from fastapi import FastAPI
from fastkit_core.validation import BaseCreateSchema, min_length

app = FastAPI()

class ProductCreate(BaseCreateSchema):
    name: str = min_length(3)
    price: float
    stock: int

@app.post("/products")
def create_product(product: ProductCreate):
    # FastAPI validates automatically
    # Returns 422 with structured errors if validation fails
    return {"message": "Product created", "product": product.to_dict()}
```

### Manual Validation with Helpers

```python
from fastkit_core.http import success_response, error_response
from pydantic import ValidationError

@app.post("/products")
def create_product(data: dict):
    try:
        product = ProductCreate(**data)
        return success_response(data=product.to_dict())
    except ValidationError as e:
        errors = ProductCreate.format_errors(e)
        return error_response(message="Validation failed", errors=errors, status_code=422)
```

### Global Exception Handler

FastKit Core provides built-in exception handlers via `register_exception_handlers()`.
See the [HTTP utilities documentation](http_utilities.md) for details.

---

<a name="custom-validators"></a>
## Custom Validators

### Field Validators

```python
from fastkit_core.validation import BaseCreateSchema
from fastkit_core.i18n import _
from pydantic import field_validator

class UserCreate(BaseCreateSchema):
    username: str
    bio: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError(_('validation.username.min_length', min=3))
        if not v.isalnum():
            raise ValueError(_('validation.username.format'))
        return v

    @field_validator('bio')
    @classmethod
    def clean_bio(cls, v: str) -> str:
        # Strip extra whitespace before storing
        return ' '.join(v.split())
```

### Model Validators (Cross-Field)

```python
from fastkit_core.validation import BaseCreateSchema
from pydantic import model_validator
from datetime import date

class EventCreate(BaseCreateSchema):
    title: str
    start_date: date
    end_date: date

    @model_validator(mode='after')
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError('End date must be after start date')
        return self
```

### Custom Validator Mixin

```python
from fastkit_core.validation import BaseCreateSchema
from fastkit_core.i18n import _
from pydantic import field_validator
from typing import ClassVar
import re

class PhoneValidatorMixin:
    PHONE_PATTERN: ClassVar[str] = r'^\+?1?\d{9,15}$'
    VALIDATION_MSG_PHONE_KEY: ClassVar[str] = 'validation.phone.format'

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(cls.PHONE_PATTERN, v):
            raise ValueError(_(cls.VALIDATION_MSG_PHONE_KEY))
        return v

class UserCreate(BaseCreateSchema, PhoneValidatorMixin):
    name: str
    phone: str
```

---

<a name="error-helpers"></a>
## Error Helpers

Helper functions for raising and formatting validation errors programmatically —
useful in services, repositories, and exception handlers.

### raise_validation_error

Raise a `ValidationError` for a single field:

```python
from fastkit_core.validation import raise_validation_error

def create_user(email: str):
    if user_exists(email):
        raise_validation_error('email', 'Email already exists', email)
```

Parameters: `field: str`, `message: str`, `value: Any = None`

### raise_multiple_validation_errors

Raise a `ValidationError` with multiple field errors at once:

```python
from fastkit_core.validation import raise_multiple_validation_errors

def create_transfer(from_account: str, to_account: str, amount: float):
    errors = []

    if not account_exists(from_account):
        errors.append(('from_account', 'Account not found', from_account))

    if not account_exists(to_account):
        errors.append(('to_account', 'Account not found', to_account))

    if amount <= 0:
        errors.append(('amount', 'Amount must be positive', amount))

    if errors:
        raise_multiple_validation_errors(errors)
```

Parameters: `errors: list[tuple[str, str, Any]]` — list of `(field, message, value)` tuples.

### format_validation_errors

Parse a raw Pydantic/FastAPI error list into `{field: [messages]}` format:

```python
from fastkit_core.validation import format_validation_errors

try:
    schema = UserCreate(**data)
except ValidationError as e:
    errors = format_validation_errors(e.errors())
    # {'email': ['Field required'], 'password': ['Too short', 'Needs uppercase']}
```

Used internally by FastKit's exception handlers to ensure consistent formatting
across both `RequestValidationError` (FastAPI) and `ValidationError` (Pydantic).
For nested field locations (e.g. `('body', 'address', 'city')`), the last element
is used as the field name. Errors without a location are grouped under `'unknown'`.

---

<a name="best-practices"></a>
## Best Practices

### 1. Use the Right Base Class for Each Schema

✅ **Good:**
```python
from fastkit_core.validation import BaseCreateSchema, BaseUpdateSchema, BaseSchema

class UserCreate(BaseCreateSchema):    # input — extra fields forbidden
    name: str
    email: str

class UserUpdate(BaseUpdateSchema):    # partial input — extra fields forbidden
    name: str | None = None
    email: str | None = None

class UserResponse(BaseSchema):        # output — ORM-ready
    id: int
    name: str
    email: str
```

❌ **Bad:**
```python
class UserCreate(BaseModel):     # Missing from_attributes, missing extra='forbid'
    name: str
    email: str

class UserResponse(BaseModel):   # Must remember model_config on every response schema
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)  # Easy to forget
```

### 2. Separate Schemas by Operation

```python
class ProductCreate(BaseCreateSchema):
    """Schema for creating products — required fields only."""
    name: str
    price: float
    stock: int

class ProductUpdate(BaseUpdateSchema):
    """Schema for updating products — all fields optional."""
    name: str | None = None
    price: float | None = None
    stock: int | None = None

class ProductResponse(BaseSchema):
    """Schema for product responses — includes computed fields."""
    id: int
    name: str
    price: float
    stock: int
    created_at: datetime
```

### 3. Use Computed Fields for Derived Properties

✅ **Good:**
```python
from pydantic import computed_field

class UserResponse(BaseSchema):
    first_name: str
    last_name: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

# full_name is automatically included in to_dict() and to_json_str()
user_response.to_dict()
# {'first_name': 'Alice', 'last_name': 'Smith', 'full_name': 'Alice Smith'}
```

❌ **Bad:**
```python
# Manually constructing derived fields in every endpoint
@app.get("/users/{id}")
def get_user(id: int):
    user = repo.get(id)
    data = user.to_dict()
    data['full_name'] = f"{user.first_name} {user.last_name}"  # Easy to forget
    return data
```

### 4. Use Mixins for Reusable Validation

✅ **Good:**
```python
class UserCreate(BaseCreateSchema, UsernameValidatorMixin, PasswordValidatorMixin):
    username: str
    password: str
    email: str
```

❌ **Bad:**
```python
class UserCreate(BaseCreateSchema):
    username: str
    password: str

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        # Duplicate validation logic in every schema
        if len(v) < 3:
            raise ValueError("Too short")
        ...
```

### 5. Use to_dict() in API Responses

✅ **Good:**
```python
@app.get("/users/{id}")
def get_user(id: int):
    user = repo.get(id)
    response = UserResponse.model_validate(user)

    # Exclude None fields from API response
    return success_response(data=response.to_dict(exclude_none=True))
```

❌ **Bad:**
```python
@app.get("/users/{id}")
def get_user(id: int):
    user = repo.get(id)
    # model_dump() everywhere instead of the helper
    return {"data": UserResponse.model_validate(user).model_dump(exclude_none=True)}
```

### 6. Provide Translated Error Messages

Always create translations for custom validators:

```python
# validators.py
@field_validator('code')
@classmethod
def validate_code(cls, v: str) -> str:
    if not v.startswith('PRD-'):
        raise ValueError(_('validation.product_code.format'))
    return v
```
```json
// translations/en.json
{
  "validation": {
    "product_code": {
      "format": "Product code must start with 'PRD-'"
    }
  }
}
```

### 7. Document Schema Fields

```python
from pydantic import Field
from fastkit_core.validation import BaseCreateSchema

class UserCreate(BaseCreateSchema):
    username: str = Field(
        min_length=3,
        max_length=20,
        description="Unique username for the user"
    )
    email: str = Field(description="User's email address")
    age: int = Field(ge=13, le=120, description="User's age")
```

### 8. Test Validation Logic

```python
def test_user_validation():
    """Test user schema validation."""
    # Valid data
    user = UserCreate(
        username="alice",
        email="alice@example.com",
        password="SecurePass1!"
    )
    assert user.username == "alice"

    # Invalid username
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            username="ab",  # Too short
            email="alice@example.com",
            password="SecurePass1!"
        )

    errors = UserCreate.format_errors(exc.value)
    assert "username" in errors

    # Extra field — forbidden by BaseCreateSchema
    with pytest.raises(ValidationError):
        UserCreate(
            username="alice",
            email="alice@example.com",
            password="SecurePass1!",
            role="admin"  # Not allowed
        )
```

---

<a name="api-reference"></a>
## API Reference

### BaseSchema

```
class BaseSchema(BaseModel)

model_config: ConfigDict(from_attributes=True)

# Class methods
format_errors(errors: ValidationError) -> dict[str, list[str]]
config_exclude_none() -> ConfigDict
config_exclude_fields(fields: list[str]) -> ConfigDict

# Instance methods
to_dict(exclude_none: bool = False) -> dict[str, Any]
to_json_str(exclude_none: bool = False) -> str
```

`from_attributes=True` is set on `BaseSchema` and inherited by all subclasses.
There is no need to redeclare `model_config` on response schemas.

### BaseCreateSchema

```
class BaseCreateSchema(BaseSchema)

model_config: ConfigDict(from_attributes=True, extra='forbid')
```

Use for create input schemas. Extra fields raise `ValidationError` with type `extra_forbidden`.

### BaseUpdateSchema

```
class BaseUpdateSchema(BaseSchema)

model_config: ConfigDict(from_attributes=True, extra='forbid')
```

Use for update input schemas. By convention all fields should be `Optional` with `None`
default to support partial updates via `model_dump(exclude_unset=True)`.

### Validation Rules

```
min_length(length: int)            → Field(min_length=length)
max_length(length: int)            → Field(max_length=length)
length(min_len: int, max_len: int) → Field(min_length=..., max_length=...)
min_value(value: int | float)      → Field(ge=value)
max_value(value: int | float)      → Field(le=value)
between(min_val, max_val)          → Field(ge=min_val, le=max_val)
pattern(regex: str)                → Field(pattern=regex)
```

### Validator Mixins

```
PasswordValidatorMixin
    PWD_MIN_LENGTH: ClassVar[int] = 8
    PWD_MAX_LENGTH: ClassVar[int] = 16
    Validates: field named 'password'

StrongPasswordValidatorMixin
    PWD_MIN_LENGTH: ClassVar[int] = 10
    PWD_MAX_LENGTH: ClassVar[int] = 20
    Validates: field named 'password' (uppercase + lowercase + digit + special)

UsernameValidatorMixin
    USM_MIN_LENGTH: ClassVar[int] = 3
    USM_MAX_LENGTH: ClassVar[int] = 20
    Validates: field named 'username'

SlugValidatorMixin
    Validates: field named 'slug'
```

### Error Helpers

```
raise_validation_error(field: str, message: str, value: Any = None) -> None
raise_multiple_validation_errors(errors: list[tuple[str, str, Any]]) -> None
format_validation_errors(errors: list[dict]) -> dict[str, list[str]]
```

---

## Complete Example

```python
# schemas.py
from fastkit_core.validation import (
    BaseSchema,
    BaseCreateSchema,
    BaseUpdateSchema,
    UsernameValidatorMixin,
    PasswordValidatorMixin,
    min_length,
    between,
)
from pydantic import EmailStr, Field, computed_field
from datetime import datetime

class UserCreate(BaseCreateSchema, UsernameValidatorMixin, PasswordValidatorMixin):
    """Create schema — extra fields forbidden."""
    username: str
    email: EmailStr
    password: str
    full_name: str = min_length(2)
    age: int = between(13, 120)

class UserUpdate(BaseUpdateSchema):
    """Update schema — partial updates, extra fields forbidden."""
    full_name: str | None = None
    age: int | None = Field(None, ge=13, le=120)

class UserResponse(BaseSchema):
    """Response schema — ORM-ready, computed fields supported."""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    age: int
    created_at: datetime

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
```

```python
# main.py
from fastapi import FastAPI, Depends, Header
from fastkit_core.http import success_response, error_response
from fastkit_core.i18n import set_locale
from pydantic import ValidationError

app = FastAPI()

async def detect_language(accept_language: str = Header(default='en')):
    set_locale(accept_language[:2])

@app.post("/users", dependencies=[Depends(detect_language)])
def create_user(data: dict):
    try:
        user = UserCreate(**data)
        # ... save to database
        return success_response(data={"id": 1}, status_code=201)
    except ValidationError as e:
        errors = UserCreate.format_errors(e)
        return error_response(message="Validation failed", errors=errors, status_code=422)

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user_orm = db.get(User, user_id)
    # from_attributes=True — no extra config needed
    response = UserResponse.model_validate(user_orm)
    return success_response(data=response.to_dict(exclude_none=True))
```

---

## Next Steps

- **[Translations](translations.md)** — Configure i18n for validation messages
- **[HTTP](http_utilities.md)** — Standardized error responses and exception handlers
- **[Services](services.md)** — Use validation schemas in the service layer
