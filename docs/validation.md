# Validation

- [Introduction](#introduction)
- [Quick Example](#quick-example)
- [BaseSchema](#baseschema)
- [Validation Rules](#validation-rules)
- [Validator Mixins](#validator-mixins)
- [Translated Error Messages](#translated-error-messages)
- [API Integration](#api-integration)
- [Custom Validators](#custom-validators)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's validation system is built on top of Pydantic, adding automatic 
translation of error messages, reusable validator mixins, and convenient validation rules.

**Key Features:**

- **Pydantic-based** - Leverages Pydantic's powerful validation
- **Translated Errors** - Automatic translation of validation messages
- **Reusable Mixins** - Common validators (password, username, slug)
- **Simple Rules** - Helper functions for common validations
- **Structured Errors** - Clean error format for APIs
- **Multi-language** - Error messages in user's language
- **Type-safe** - Full type checking support

---

<a name="quick-example"></a>
## Quick Example

**Define a schema with validation:**
```python
from fastkit_core.validation import BaseSchema, min_length, PasswordValidatorMixin
from pydantic import EmailStr

class UserCreate(BaseSchema, PasswordValidatorMixin):
    """User registration schema with validation."""
    username: str = min_length(3)
    email: EmailStr
    password: str  # Validated by PasswordValidatorMixin
    age: int | None = None
```

**Use in FastAPI:**
```python
from fastapi import FastAPI, HTTPException
from fastkit_core.http import error_response

app = FastAPI()

@app.post("/users")
def create_user(user: UserCreate):
    # If validation fails, FastAPI automatically returns 422
    # with structured error messages
    return {"message": "User created"}

# Or handle validation manually
@app.post("/users/manual")
def create_user_manual(data: dict):
    try:
        user = UserCreate(**data)
        return {"message": "User created"}
    except ValidationError as e:
        # Format errors with translations
        errors = UserCreate.format_errors(e)
        return error_response(
            message="Validation failed",
            errors=errors,
            status_code=422
        )
```

**Error response:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "username": ["The username must be at least 3 characters"],
    "email": ["The email must be a valid email address"],
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

`BaseSchema` is the foundation of validation in FastKit Core. It extends Pydantic's 
`BaseModel` with automatic error translation and formatting.

### Basic Usage
```python
from fastkit_core.validation import BaseSchema

class ProductCreate(BaseSchema):
    name: str
    price: float
    description: str | None = None
    in_stock: bool = True
```

### Error Formatting

`BaseSchema` provides `format_errors()` for clean error messages:
```python
from pydantic import ValidationError

try:
    product = ProductCreate(
        name="",  # Too short
        price=-10,  # Negative
    )
except ValidationError as e:
    errors = ProductCreate.format_errors(e)
    print(errors)
    # {
    #     "name": ["String should have at least 1 character"],
    #     "price": ["Input should be greater than 0"]
    # }
```

### Translated Errors

Errors are automatically translated based on current locale:
```python
from fastkit_core.i18n import set_locale
from pydantic import ValidationError

# Set Spanish locale
set_locale('es')

try:
    product = ProductCreate(name="", price=-10)
except ValidationError as e:
    errors = ProductCreate.format_errors(e)
    # Errors in Spanish
    # {
    #     "name": ["El campo nombre debe tener al menos 1 carácter"],
    #     "price": ["El valor debe ser mayor que 0"]
    # }
```

### Validation Message Mapping

`BaseSchema` maps Pydantic error types to translation keys:
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

Create corresponding translations in `translations/en.json`:
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

<a name="validation-rules"></a>
## Validation Rules

FastKit Core provides convenient helper functions for common validation rules.

### String Length
```python
from fastkit_core.validation import BaseSchema, min_length, max_length, length

class PostCreate(BaseSchema):
    title: str = min_length(5)              # At least 5 characters
    slug: str = max_length(100)             # At most 100 characters
    excerpt: str = length(10, 200)          # Between 10-200 characters
```

### Numeric Ranges
```python
from fastkit_core.validation import BaseSchema, min_value, max_value, between

class ProductCreate(BaseSchema):
    price: float = min_value(0.01)          # At least 0.01
    stock: int = max_value(1000)            # At most 1000
    rating: float = between(1.0, 5.0)       # Between 1.0 and 5.0
```

### Pattern Matching
```python
from fastkit_core.validation import BaseSchema, pattern

class CodeCreate(BaseSchema):
    hex_color: str = pattern(r'^#[0-9A-Fa-f]{6}$')  # Hex color
    phone: str = pattern(r'^\+?1?\d{9,15}$')         # Phone number
```

### Combining Rules
```python
from fastkit_core.validation import BaseSchema, length
from pydantic import Field

class UserCreate(BaseSchema):
    # Multiple constraints
    username: str = Field(min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    
    # Or use helper
    bio: str = length(10, 500)
```

---

<a name="validator-mixins"></a>
## Validator Mixins

FastKit Core provides reusable validator mixins for common patterns.

### PasswordValidatorMixin

Standard password validation (8-16 characters, uppercase, special character):
```python
from fastkit_core.validation import BaseSchema, PasswordValidatorMixin

class UserCreate(BaseSchema, PasswordValidatorMixin):
    username: str
    email: str
    password: str  # Automatically validated by mixin

# Requirements:
# - 8-16 characters
# - At least one uppercase letter
# - At least one special character (!@#$%^&*(),.?":{}|<>)
```

**Customize requirements:**
```python
class CustomPasswordSchema(BaseSchema, PasswordValidatorMixin):
    PWD_MIN_LENGTH = 10  # Override minimum length
    PWD_MAX_LENGTH = 30  # Override maximum length
    
    password: str
```

### StrongPasswordValidatorMixin

Stronger password validation (10-20 characters, all requirements):
```python
from fastkit_core.validation import BaseSchema, StrongPasswordValidatorMixin

class AdminCreate(BaseSchema, StrongPasswordValidatorMixin):
    username: str
    password: str  # Requires uppercase, lowercase, digit, special char

# Requirements:
# - 10-20 characters
# - At least one uppercase letter
# - At least one lowercase letter
# - At least one digit
# - At least one special character
```

### UsernameValidatorMixin

Username validation (3-20 characters, alphanumeric + underscore):
```python
from fastkit_core.validation import BaseSchema, UsernameValidatorMixin

class UserCreate(BaseSchema, UsernameValidatorMixin):
    username: str  # Automatically validated
    email: str

# Requirements:
# - 3-20 characters
# - Alphanumeric and underscore only
# - Cannot start with a number
```

**Customize:**
```python
class CustomUsernameSchema(BaseSchema, UsernameValidatorMixin):
    USM_MIN_LENGTH = 5   # Override min length
    USM_MAX_LENGTH = 15  # Override max length
    
    username: str
```

### SlugValidatorMixin

URL-friendly slug validation:
```python
from fastkit_core.validation import BaseSchema, SlugValidatorMixin

class PostCreate(BaseSchema, SlugValidatorMixin):
    title: str
    slug: str  # Automatically validated

# Requirements:
# - Lowercase letters, numbers, hyphens only
# - No consecutive hyphens
# - Cannot start/end with hyphen
```

**Valid slugs:**
- ✅ `hello-world`
- ✅ `fastkit-core-2024`
- ✅ `my-awesome-post`

**Invalid slugs:**
- ❌ `Hello-World` (uppercase)
- ❌ `hello--world` (consecutive hyphens)
- ❌ `-hello-world` (starts with hyphen)

### Combining Multiple Mixins
```python
from fastkit_core.validation import (
    BaseSchema,
    UsernameValidatorMixin,
    PasswordValidatorMixin
)

class UserRegistration(
    BaseSchema,
    UsernameValidatorMixin,
    PasswordValidatorMixin
):
    username: str
    password: str
    email: str
    
# Both username and password are validated!
```

---

<a name="translated-error-messages"></a>
## Translated Error Messages

All validation errors are automatically translated based on the user's locale.

### Setup Translation Files
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
```json
// translations/es.json
{
  "validation": {
    "required": "El campo {field} es obligatorio",
    "string_too_short": "El {field} debe tener al menos {min_length} caracteres",
    "string_too_long": "El {field} no debe exceder {max_length} caracteres",
    "email": "El {field} debe ser una dirección de correo válida",
    "password": {
      "min_length": "La contraseña debe tener al menos {min} caracteres",
      "uppercase": "La contraseña debe contener al menos una letra mayúscula",
      "special_char": "La contraseña debe contener al menos un carácter especial"
    }
  }
}
```

### Usage with Locale
```python
from fastapi import FastAPI, Depends, Header
from fastkit_core.i18n import set_locale
from fastkit_core.validation import BaseSchema, PasswordValidatorMixin
from pydantic import ValidationError

app = FastAPI()

async def detect_language(accept_language: str = Header(default='en')):
    language = accept_language.split(',')[0].split('-')[0]
    set_locale(language)

class UserCreate(BaseSchema, PasswordValidatorMixin):
    username: str
    password: str

@app.post("/users", dependencies=[Depends(detect_language)])
def create_user(data: dict):
    try:
        user = UserCreate(**data)
        return {"message": "User created"}
    except ValidationError as e:
        # Errors automatically translated to user's language
        errors = UserCreate.format_errors(e)
        return {"errors": errors}, 422
```

**Test with different languages:**
```bash
# English errors
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username": "a", "password": "weak"}'

# Spanish errors
curl -X POST http://localhost:8000/users \
  -H "Accept-Language: es" \
  -H "Content-Type: application/json" \
  -d '{"username": "a", "password": "weak"}'
```

---

<a name="api-integration"></a>
## API Integration

### FastAPI Integration

FastAPI automatically validates request data using Pydantic schemas:
```python
from fastapi import FastAPI
from fastkit_core.validation import BaseSchema, min_length

app = FastAPI()

class ProductCreate(BaseSchema):
    name: str = min_length(3)
    price: float
    stock: int

@app.post("/products")
def create_product(product: ProductCreate):
    # FastAPI automatically validates
    # Returns 422 with errors if validation fails
    return {
        "message": "Product created",
        "product": product.model_dump()
    }
```

### Manual Validation

For more control over error handling:
```python
from fastapi import FastAPI
from fastkit_core.http import success_response, error_response
from pydantic import ValidationError

app = FastAPI()

@app.post("/products")
def create_product(data: dict):
    try:
        product = ProductCreate(**data)
        # Process product...
        return success_response(
            data=product.model_dump(),
            message="Product created successfully"
        )
    except ValidationError as e:
        errors = ProductCreate.format_errors(e)
        return error_response(
            message="Validation failed",
            errors=errors,
            status_code=422
        )
```

### Exception Handler

Create a global validation error handler:
```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastkit_core.http import error_response

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors globally."""
    # Format Pydantic errors
    errors = {}
    for error in exc.errors():
        field = error['loc'][-1]
        if field not in errors:
            errors[field] = []
        errors[field].append(error['msg'])
    
    return error_response(
        message="Validation failed",
        errors=errors,
        status_code=422
    )
```

### With Dependency Injection
```python
from fastapi import FastAPI, Depends
from pydantic import ValidationError

app = FastAPI()

async def validate_product(data: dict) -> ProductCreate:
    """Validate product data with custom error handling."""
    try:
        return ProductCreate(**data)
    except ValidationError as e:
        errors = ProductCreate.format_errors(e)
        # Handle errors...
        raise HTTPException(status_code=422, detail=errors)

@app.post("/products")
def create_product(product: ProductCreate = Depends(validate_product)):
    return {"message": "Product created"}
```

---

<a name="custom-validators"></a>
## Custom Validators

### Field Validators

Create custom validation logic using Pydantic's `field_validator`:
```python
from fastkit_core.validation import BaseSchema
from fastkit_core.i18n import _
from pydantic import field_validator
import re

class UserCreate(BaseSchema):
    username: str
    email: str
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
    def validate_bio(cls, v: str) -> str:
        # Remove extra whitespace
        v = ' '.join(v.split())
        
        if len(v) > 500:
            raise ValueError(_('validation.string_too_long', 
                             field='bio', 
                             max_length=500))
        
        return v
```

### Model Validators

Validate relationships between fields:
```python
from fastkit_core.validation import BaseSchema
from fastkit_core.i18n import _
from pydantic import model_validator
from datetime import date

class EventCreate(BaseSchema):
    title: str
    start_date: date
    end_date: date
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Ensure end_date is after start_date."""
        if self.end_date < self.start_date:
            raise ValueError(_('validation.end_date_before_start'))
        return self
```

### Custom Validator Mixin

Create reusable custom validators:
```python
from fastkit_core.validation import BaseSchema
from fastkit_core.i18n import _
from pydantic import field_validator
from typing import ClassVar
import re

class PhoneValidatorMixin:
    """Phone number validation mixin."""
    PHONE_PATTERN: ClassVar[str] = r'^\+?1?\d{9,15}$'
    VALIDATION_MSG_PHONE_KEY: ClassVar[str] = 'validation.phone.format'
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(cls.PHONE_PATTERN, v):
            raise ValueError(_(cls.VALIDATION_MSG_PHONE_KEY))
        return v

# Usage
class UserCreate(BaseSchema, PhoneValidatorMixin):
    name: str
    phone: str  # Automatically validated
```

---

<a name="best-practices"></a>
## Best Practices

### 1. Use Descriptive Schema Names

✅ **Good:**
```python
class UserCreateSchema(BaseSchema):
    ...

class UserUpdateSchema(BaseSchema):
    ...

class UserResponseSchema(BaseSchema):
    ...
```

❌ **Bad:**
```python
class User(BaseSchema):  # Too generic
    ...

class UserSchema(BaseSchema):  # What operation?
    ...
```

### 2. Separate Schemas by Operation
```python
class ProductCreate(BaseSchema):
    """Schema for creating products."""
    name: str
    price: float
    stock: int

class ProductUpdate(BaseSchema):
    """Schema for updating products."""
    name: str | None = None
    price: float | None = None
    stock: int | None = None

class ProductResponse(BaseSchema):
    """Schema for product responses."""
    id: int
    name: str
    price: float
    stock: int
    created_at: datetime
```

### 3. Use Mixins for Reusable Validation

✅ **Good:**
```python
class UserCreate(BaseSchema, UsernameValidatorMixin, PasswordValidatorMixin):
    username: str
    password: str
    email: str
```

❌ **Bad:**
```python
class UserCreate(BaseSchema):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        # Duplicate validation logic in every schema
        ...
```

### 4. Provide Translated Error Messages

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

### 5. Use Helpers for Common Rules

✅ **Good:**
```python
from fastkit_core.validation import min_length, between

class ProductCreate(BaseSchema):
    name: str = min_length(3)
    rating: float = between(1.0, 5.0)
```

❌ **Bad:**
```python
from pydantic import Field

class ProductCreate(BaseSchema):
    name: str = Field(min_length=3)  # More verbose
    rating: float = Field(ge=1.0, le=5.0)
```

### 6. Document Schema Fields
```python
from fastkit_core.validation import BaseSchema
from pydantic import Field

class UserCreate(BaseSchema):
    username: str = Field(
        min_length=3,
        max_length=20,
        description="Unique username for the user"
    )
    email: str = Field(description="User's email address")
    age: int = Field(ge=13, le=120, description="User's age")
```

### 7. Test Validation Logic
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
```

---

<a name="api-reference"></a>
## API Reference

### BaseSchema
```python
class BaseSchema(BaseModel):
    """Base schema with translation support."""
    
    VALIDATION_MESSAGE_MAP: ClassVar[Dict[str, str]]
    
    @classmethod
    def format_errors(cls, errors: ValidationError) -> Dict[str, List[str]]:
        """
        Format validation errors with translations.
        
        Args:
            errors: Pydantic ValidationError
            
        Returns:
            Dictionary mapping field names to error messages
            
        Example:
            {
                "username": ["Username must be at least 3 characters"],
                "email": ["Invalid email format"]
            }
        """
```

---

### Validation Rules

**`min_length(length: int)`**

Minimum string length constraint.
```python
name: str = min_length(3)
```

**`max_length(length: int)`**

Maximum string length constraint.
```python
name: str = max_length(100)
```

**`length(min_len: int, max_len: int)`**

String length range constraint.
```python
bio: str = length(10, 500)
```

**`min_value(value: int | float)`**

Minimum numeric value constraint.
```python
price: float = min_value(0.01)
```

**`max_value(value: int | float)`**

Maximum numeric value constraint.
```python
stock: int = max_value(1000)
```

**`between(min_val: int | float, max_val: int | float)`**

Numeric range constraint.
```python
rating: float = between(1.0, 5.0)
```

**`pattern(regex: str)`**

Regular expression pattern constraint.
```python
hex_color: str = pattern(r'^#[0-9A-Fa-f]{6}$')
```

---

### Validator Mixins

**`PasswordValidatorMixin`**

Standard password validation (8-16 chars, uppercase, special char).
```python
class UserCreate(BaseSchema, PasswordValidatorMixin):
    password: str

# Customizable:
PWD_MIN_LENGTH: ClassVar[int] = 8
PWD_MAX_LENGTH: ClassVar[int] = 16
```

**`StrongPasswordValidatorMixin`**

Strong password validation (10-20 chars, all requirements).
```python
class AdminCreate(BaseSchema, StrongPasswordValidatorMixin):
    password: str

# Customizable:
PWD_MIN_LENGTH: ClassVar[int] = 10
PWD_MAX_LENGTH: ClassVar[int] = 20
```

**`UsernameValidatorMixin`**

Username validation (3-20 chars, alphanumeric + underscore).
```python
class UserCreate(BaseSchema, UsernameValidatorMixin):
    username: str

# Customizable:
USM_MIN_LENGTH: ClassVar[int] = 3
USM_MAX_LENGTH: ClassVar[int] = 20
```

**`SlugValidatorMixin`**

URL-friendly slug validation.
```python
class PostCreate(BaseSchema, SlugValidatorMixin):
    slug: str
```

---

## Complete Example
```python
# schemas.py
from fastkit_core.validation import (
    BaseSchema,
    UsernameValidatorMixin,
    PasswordValidatorMixin,
    min_length
)
from pydantic import EmailStr, Field

class UserCreate(BaseSchema, UsernameValidatorMixin, PasswordValidatorMixin):
    """User registration schema."""
    username: str
    email: EmailStr
    password: str
    full_name: str = min_length(2)
    age: int = Field(ge=13, le=120)

class UserUpdate(BaseSchema):
    """User update schema."""
    full_name: str | None = None
    age: int | None = Field(None, ge=13, le=120)

class UserResponse(BaseSchema):
    """User response schema."""
    id: int
    username: str
    email: str
    full_name: str
    
    model_config = {"from_attributes": True}
```
```python
# main.py
from fastapi import FastAPI, Depends, Header
from fastkit_core.http import success_response, error_response
from fastkit_core.i18n import set_locale
from pydantic import ValidationError
from schemas import UserCreate, UserResponse

app = FastAPI()

async def detect_language(accept_language: str = Header(default='en')):
    language = accept_language.split(',')[0].split('-')[0]
    set_locale(language)

@app.post("/users", dependencies=[Depends(detect_language)])
def create_user(data: dict):
    try:
        user = UserCreate(**data)
        # Create user in database...
        return success_response(
            data={"id": 1, "username": user.username},
            message="User created successfully"
        )
    except ValidationError as e:
        errors = UserCreate.format_errors(e)
        return error_response(
            message="Validation failed",
            errors=errors,
            status_code=422
        )
```
```json
// translations/en.json
{
  "validation": {
    "required": "The {field} field is required",
    "string_too_short": "The {field} must be at least {min_length} characters",
    "email": "The {field} must be a valid email address",
    "greater_than_equal": "The {field} must be at least {ge}",
    "password": {
      "min_length": "Password must be at least {min} characters",
      "uppercase": "Password must contain at least one uppercase letter",
      "special_char": "Password must contain at least one special character"
    },
    "username": {
      "min_length": "Username must be at least {min} characters",
      "format": "Username must contain only letters, numbers, and underscores"
    }
  }
}
```

---

## Next Steps

Now that you understand validation, explore:

- **[Translations](translations.md)** - Learn how validation uses translations
- **[HTTP](http_utilities.md)** - Standardized error responses
- **[Services](services.md)** - Use validation in service layer
