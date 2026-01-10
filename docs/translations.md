# Translations

- [Introduction](#introduction)
- [Quick Example](#quick-example)
- [Setup](#setup)
- [Translation Files](#translation-files)
- [Using Translations](#using-translations)
- [Configuration](#configuration)
- [API Integration](#api-integration)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's translation system makes it easy to build multi-language applications. 
Whether you're translating validation messages, API responses, or model content, 
FastKit has you covered. Even if you use only one language in your application, 
with JSON structure you have easy control of system labels and can manage them in one place.

**Key Features:**

- ✅ **JSON-based** - Simple, readable translation files
- ✅ **Automatic Language Detection** - From `Accept-Language` header
- ✅ **Fallback Support** - Graceful degradation to default language
- ✅ **Translatable Models** - Store multi-language content in database (see [Database](/docs/database))
- ✅ **Nested Keys** - Organize translations hierarchically
- ✅ **Parameter Substitution** - Dynamic content in translations
- ✅ **Easy Access** - Helper functions for quick dot notation access
- ✅ **Context Variables** - Shared locale context across application
- ✅ **Zero Configuration** - Works out of the box

---

<a name="quick-example"></a>
## Quick Example

**Create translation files:**
```json
// translations/en.json
{
  "messages": {
    "welcome": "Welcome to FastKit Core!",
    "hello": "Hello, {name}!",
    "items_count": "You have {count} items"
  },
  "auth": {
    "login": "Log In",
    "logout": "Log Out"
  }
}

// translations/es.json
{
  "messages": {
    "welcome": "¡Bienvenido a FastKit Core!",
    "hello": "¡Hola, {name}!",
    "items_count": "Tienes {count} artículos"
  },
  "auth": {
    "login": "Iniciar Sesión",
    "logout": "Cerrar Sesión"
  }
}
```

**Use in your code:**
```python
from fastkit_core.i18n import _, set_locale

# Simple translation
greeting = _('messages.welcome')  
# "Welcome to FastKit Core!"

# With parameters
hello = _('messages.hello', name='Alice')  
# "Hello, Alice!"

# Change language
set_locale('es')
greeting_es = _('messages.welcome')  
# "¡Bienvenido a FastKit Core!"

# Force specific locale
login_fr = _('auth.login', locale='fr')
# "Connexion" (if fr.json exists)
```

That's the basics! Now let's dive deeper.

---

<a name="setup"></a>
## Setup

### Directory Structure

Create a `translations/` directory in your project root:
```
your-project/
├── translations/
│   ├── en.json          # English (default)
│   ├── es.json          # Spanish
│   ├── fr.json          # French
│   ├── de.json          # German
│   └── ...
├── config/
│   └── app.py
├── main.py
└── .env
```

> **Note:** Default directory is `translations/`. You can configure this in 
> `config/app.py` with `TRANSLATIONS_PATH` setting.

### Automatic Initialization

FastKit Core automatically initializes the translation manager when you first use it:
```python
from fastkit_core.i18n import _

# First call creates the global manager
text = _('messages.welcome')
```

### Manual Initialization

For more control, initialize explicitly:
```python
from fastkit_core.i18n import TranslationManager, set_translation_manager

# Create custom manager
manager = TranslationManager(translations_dir='lang')

# Set as global
set_translation_manager(manager)
```

---

<a name="translation-files"></a>
## Translation Files

### File Format

Translation files are JSON with nested structure:
```json
{
  "app": {
    "name": "My Application",
    "tagline": "Built with FastKit Core"
  },
  "auth": {
    "login": "Log In",
    "logout": "Log Out",
    "welcome": "Welcome back, {username}!"
  },
  "messages": {
    "success": "Operation completed successfully",
    "error": "Something went wrong",
    "saved": "{model} saved successfully"
  },
  "validation": {
    "required": "The {field} field is required",
    "email": "The {field} must be a valid email address",
    "min_length": "The {field} must be at least {min} characters"
  }
}
```

### Nested Keys

Organize translations hierarchically and access with dot notation:
```python
from fastkit_core.i18n import _

# Access nested keys
app_name = _('app.name')              # "My Application"
login = _('auth.login')                # "Log In"
success = _('messages.success')        # "Operation completed..."
email_error = _('validation.email')    # "The {field} must be..."
```

### Parameter Substitution

Use `{parameter}` placeholders for dynamic content:
```json
{
  "greetings": {
    "hello": "Hello, {name}!",
    "welcome": "Welcome, {name}. You have {count} new messages."
  },
  "notifications": {
    "friend_request": "{sender} sent you a friend request",
    "comment": "{user} commented on your post: {comment}"
  }
}
```

Use parameters when translating:
```python
from fastkit_core.i18n import _

# Single parameter
greeting = _('greetings.hello', name='Alice')
# "Hello, Alice!"

# Multiple parameters
welcome = _('greetings.welcome', name='Bob', count=5)
# "Welcome, Bob. You have 5 new messages."

# Complex example
notification = _('notifications.comment', 
                 user='Charlie', 
                 comment='Great post!')
# "Charlie commented on your post: Great post!"
```

### Language Codes

Use ISO 639-1 language codes:
```
en    - English
es    - Spanish
fr    - French
de    - German
it    - Italian
pt    - Portuguese
nl    - Dutch
ru    - Russian
zh    - Chinese
ja    - Japanese
ko    - Korean
ar    - Arabic
```

### File Naming

Simply name files with the language code:
```
translations/
├── en.json       # English
├── es.json       # Spanish
├── fr.json       # French
├── de.json       # German
└── pt.json       # Portuguese
```

---

<a name="using-translations"></a>
## Using Translations

### Helper Function: `_()`

The `_()` function is the quickest way to translate:
```python
from fastkit_core.i18n import _

# Simple translation
message = _('messages.success')

# With parameters
greeting = _('messages.hello', name='Alice')

# With specific locale
text_es = _('messages.welcome', locale='es')

# With fallback (returns key if not found)
missing = _('missing.key')  # Returns 'missing.key'
```

### Helper Function: `gettext()`

Alias for `_()` following GNU gettext convention:
```python
from fastkit_core.i18n import gettext

message = gettext('messages.welcome')
```

### Locale Management
```python
from fastkit_core.i18n import set_locale, get_locale

# Set current locale
set_locale('es')

# Get current locale
current = get_locale()  # 'es'

# Now all translations use Spanish
welcome = _('messages.welcome')  # Spanish version
```

### Using TranslationManager Directly
```python
from fastkit_core.i18n import get_translation_manager

manager = get_translation_manager()

# Get translation
text = manager.get('messages.welcome')

# With parameters
hello = manager.get('messages.hello', name='Alice')

# Check if key exists
if manager.has('messages.custom'):
    text = manager.get('messages.custom')

# Get all translations for a locale
all_en = manager.get_all(locale='en')

# Get available locales
locales = manager.get_available_locales()  # ['en', 'es', 'fr']

# Reload translations (useful in development)
manager.reload()
```

### Fallback Behavior

If a translation is not found, FastKit Core gracefully falls back:
```python
from fastkit_core.i18n import set_locale, _

set_locale('fr')  # French

# Key exists in French
text = _('messages.welcome')  # Returns French translation

# Key missing in French, falls back to default (English)
text = _('messages.new_feature')  # Returns English translation

# Key doesn't exist anywhere, returns the key
text = _('missing.key')  # Returns 'missing.key'
```

---

<a name="configuration"></a>
## Configuration

### Application Configuration

Configure translations in `config/app.py`:
```python
# config/app.py
import os

# Translation settings
TRANSLATIONS_PATH = 'translations'  # Default directory
DEFAULT_LANGUAGE = 'en'             # Default locale
FALLBACK_LANGUAGE = 'en'            # Fallback locale
```

### Environment Variables

Override configuration with environment variables:
```bash
# .env
APP_DEFAULT_LANGUAGE=es
APP_FALLBACK_LANGUAGE=en
APP_TRANSLATIONS_PATH=lang
```
```python
# config/app.py
import os

TRANSLATIONS_PATH = os.getenv('APP_TRANSLATIONS_PATH', 'translations')
DEFAULT_LANGUAGE = os.getenv('APP_DEFAULT_LANGUAGE', 'en')
FALLBACK_LANGUAGE = os.getenv('APP_FALLBACK_LANGUAGE', 'en')
```

### Multiple Translation Directories

For different environments:
```python
from fastkit_core.i18n import TranslationManager, set_translation_manager

# Development
if DEBUG:
    manager = TranslationManager(translations_dir='translations/dev')
else:
    manager = TranslationManager(translations_dir='translations/prod')

set_translation_manager(manager)
```

---

<a name="api-integration"></a>
## API Integration

### Language Detection Middleware

Automatically detect language from `Accept-Language` header:
```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastkit_core.i18n import set_locale, get_locale

class LanguageMiddleware(BaseHTTPMiddleware):
    """Detect and set language from Accept-Language header."""
    
    async def dispatch(self, request: Request, call_next):
        # Parse Accept-Language header
        accept_language = request.headers.get('accept-language', 'en')
        # Get first language code (e.g., "en-US,en;q=0.9" -> "en")
        language = accept_language.split(',')[0].split('-')[0]
        
        # Set locale for this request
        set_locale(language)
        
        # Store in request state for easy access
        request.state.language = language
        
        response = await call_next(request)
        return response

app = FastAPI()
app.add_middleware(LanguageMiddleware)

@app.get("/")
def root():
    from fastkit_core.i18n import _, get_locale
    return {
        "message": _('messages.welcome'),
        "language": get_locale()
    }
```

### Dependency Injection

Use FastAPI's dependency injection pattern:
```python
from fastapi import FastAPI, Depends, Header
from fastkit_core.i18n import set_locale, get_locale, _

app = FastAPI()

async def detect_language(accept_language: str = Header(default='en')):
    """Detect and set language from header."""
    language = accept_language.split(',')[0].split('-')[0]
    set_locale(language)
    return language

@app.get("/")
def root(language: str = Depends(detect_language)):
    return {
        "message": _('messages.welcome'),
        "language": language
    }

@app.get("/user/{user_id}")
def get_user(
    user_id: int,
    language: str = Depends(detect_language)
):
    return {
        "user_id": user_id,
        "greeting": _('auth.welcome', username=f'User {user_id}'),
        "language": language
    }
```

### Response Formatting
```python
from fastapi import FastAPI, Depends
from fastkit_core.http import success_response
from fastkit_core.i18n import _

app = FastAPI()

@app.post("/users")
def create_user(user_data: dict, language: str = Depends(detect_language)):
    # Create user logic...
    
    return success_response(
        data={"id": 1, "username": "alice"},
        message=_('messages.user_created')
    )

@app.delete("/users/{user_id}")
def delete_user(user_id: int, language: str = Depends(detect_language)):
    # Delete user logic...
    
    return success_response(
        message=_('messages.user_deleted')
    )
```

### Complete API Example
```python
from fastapi import FastAPI, Depends, Header
from fastkit_core.http import success_response, paginated_response
from fastkit_core.i18n import set_locale, _

app = FastAPI()

async def setup_language(accept_language: str = Header(default='en')):
    """Setup language for request."""
    language = accept_language.split(',')[0].split('-')[0]
    set_locale(language)

@app.get("/", dependencies=[Depends(setup_language)])
def root():
    return {
        "message": _('messages.welcome'),
        "app_name": _('app.name')
    }

@app.post("/products", dependencies=[Depends(setup_language)])
def create_product(product: dict):
    # Create product...
    return success_response(
        data={"id": 1},
        message=_('messages.product_created', name=product['name'])
    )

@app.get("/products", dependencies=[Depends(setup_language)])
def list_products():
    # Get products...
    return paginated_response(
        items=[],
        pagination={},
        message=_('messages.products_retrieved')
    )
```

**Testing with curl:**
```bash
# English (default)
curl http://localhost:8000/

# Spanish
curl http://localhost:8000/ \
  -H "Accept-Language: es"

# French
curl http://localhost:8000/ \
  -H "Accept-Language: fr-FR,fr;q=0.9"
```

---

<a name="best-practices"></a>
## Best Practices

### 1. Organize by Feature
```json
{
  "auth": {
    "login": "Log In",
    "logout": "Log Out",
    "register": "Sign Up",
    "forgot_password": "Forgot Password?"
  },
  "products": {
    "title": "Products",
    "add": "Add Product",
    "edit": "Edit Product",
    "delete_confirm": "Delete {name}?"
  },
  "validation": {
    "required": "{field} is required",
    "email": "Invalid email format",
    "min": "{field} must be at least {min} characters"
  }
}
```

### 2. Use Consistent Key Naming

✅ **Good:**
```json
{
  "auth.login": "Log In",
  "auth.logout": "Log Out",
  "messages.success": "Success",
  "messages.error": "Error"
}
```

❌ **Bad:**
```json
{
  "loginButton": "Log In",
  "LogOut": "Log Out",
  "success_msg": "Success",
  "ERROR": "Error"
}
```

### 3. Always Provide Default Language

Ensure your default language (usually English) is 100% complete:
```
✓ en.json - 100% complete (all keys)
✓ es.json - 80% complete (falls back to English)
✓ fr.json - 60% complete (falls back to English)
```

### 4. Use Variables for Dynamic Content

✅ **Good:**
```json
{
  "greeting": "Hello, {name}!",
  "items": "You have {count} items",
  "notification": "{user} sent you {count} messages"
}
```

❌ **Bad:**
```json
{
  "greeting_alice": "Hello, Alice!",
  "greeting_bob": "Hello, Bob!",
  "one_item": "You have 1 item",
  "many_items": "You have many items"
}
```

### 5. Avoid Hardcoded Text

✅ **Good:**
```python
return success_response(
    message=_('messages.success')
)
```

❌ **Bad:**
```python
return success_response(
    message="Operation successful"  # Hardcoded!
)
```

### 6. Group Related Translations
```json
{
  "errors": {
    "not_found": "Resource not found",
    "unauthorized": "Unauthorized access",
    "server_error": "Internal server error"
  },
  "success": {
    "created": "Created successfully",
    "updated": "Updated successfully",
    "deleted": "Deleted successfully"
  }
}
```

### 7. Document Context

Add comments for translators (though JSON doesn't support comments officially, 
you can use a separate README):
```markdown
# translations/README.md

## Translation Keys

### auth
Authentication related messages
- `auth.login` - Login button text
- `auth.welcome` - Greeting shown after login (supports {username} parameter)

### messages
General application messages
- `messages.success` - Generic success message
- `messages.saved` - Shown after saving (supports {model} parameter)
```

### 8. Use .env for Language Settings
```bash
# .env
APP_DEFAULT_LANGUAGE=en
APP_FALLBACK_LANGUAGE=en
APP_TRANSLATIONS_PATH=translations
```

### 9. Test All Languages
```python
def test_translations():
    """Ensure critical keys exist in all languages."""
    from fastkit_core.i18n import TranslationManager
    
    manager = TranslationManager()
    locales = manager.get_available_locales()
    
    critical_keys = [
        'messages.welcome',
        'auth.login',
        'errors.not_found'
    ]
    
    for locale in locales:
        for key in critical_keys:
            # Check key exists
            assert manager.has(key, locale=locale), \
                f"Missing {key} in {locale}"
```

### 10. Centralize Labels

Even for single-language apps, centralize text in JSON:
```json
{
  "ui": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "edit": "Edit",
    "back": "Back"
  }
}
```

This makes it easy to:
- Change text in one place
- Prepare for future multi-language support
- Keep consistency across your app

---

<a name="api-reference"></a>
## API Reference

### TranslationManager Class
```python
class TranslationManager:
    """Manages translations from JSON files."""
    
    def __init__(
        self,
        translations_dir: str | Path | None = None
    ) -> None:
        """
        Initialize translation manager.
        
        Args:
            translations_dir: Path to translations directory.
                            If None, uses config value (default: 'translations')
        """
```

#### Methods

**`get(key: str, locale: str | None = None, fallback: bool = True, **replacements) -> str`**

Get translation for a key.
```python
# Simple
text = manager.get('messages.welcome')

# With parameters
hello = manager.get('messages.hello', name='Alice')

# Specific locale
text_es = manager.get('messages.welcome', locale='es')

# Disable fallback
text = manager.get('messages.key', fallback=False)
```

**`has(key: str, locale: str | None = None) -> bool`**

Check if translation key exists.
```python
if manager.has('messages.custom'):
    text = manager.get('messages.custom')
```

**`get_locale() -> str`**

Get current locale from context.
```python
current = manager.get_locale()  # 'en'
```

**`set_locale(locale: str) -> None`**

Set locale in context.
```python
manager.set_locale('es')
```

**`get_all(locale: str | None = None) -> dict`**

Get all translations for a locale.
```python
all_translations = manager.get_all(locale='en')
```

**`get_available_locales() -> list[str]`**

Get list of available language codes.
```python
locales = manager.get_available_locales()  # ['en', 'es', 'fr']
```

**`reload() -> None`**

Reload all translation files (useful in development).
```python
manager.reload()
```

---

### Helper Functions

**`_(key: str, locale: str | None = None, **replacements) -> str`**

Quick translation helper.
```python
from fastkit_core.i18n import _

text = _('messages.welcome')
hello = _('messages.hello', name='Alice')
text_es = _('messages.welcome', locale='es')
```

**`gettext(key: str, locale: str | None = None, **replacements) -> str`**

Alias for `_()` (GNU gettext style).
```python
from fastkit_core.i18n import gettext

text = gettext('messages.welcome')
```

**`set_locale(locale: str) -> None`**

Set current locale.
```python
from fastkit_core.i18n import set_locale

set_locale('es')
```

**`get_locale() -> str`**

Get current locale.
```python
from fastkit_core.i18n import get_locale

current = get_locale()  # 'en'
```

**`get_translation_manager() -> TranslationManager`**

Get global translation manager instance.
```python
from fastkit_core.i18n import get_translation_manager

manager = get_translation_manager()
```

**`set_translation_manager(manager: TranslationManager) -> None`**

Set custom global translation manager.
```python
from fastkit_core.i18n import TranslationManager, set_translation_manager

custom_manager = TranslationManager(translations_dir='lang')
set_translation_manager(custom_manager)
```

---

## Complete Example
```python
# config/app.py
import os

TRANSLATIONS_PATH = 'translations'
DEFAULT_LANGUAGE = os.getenv('APP_DEFAULT_LANGUAGE', 'en')
FALLBACK_LANGUAGE = 'en'
```
```json
// translations/en.json
{
  "app": {
    "name": "Task Manager"
  },
  "tasks": {
    "title": "Tasks",
    "created": "Task '{title}' created successfully",
    "completed": "{count} tasks completed",
    "empty": "No tasks yet"
  }
}
```
```json
// translations/es.json
{
  "app": {
    "name": "Gestor de Tareas"
  },
  "tasks": {
    "title": "Tareas",
    "created": "Tarea '{title}' creada con éxito",
    "completed": "{count} tareas completadas",
    "empty": "Aún no hay tareas"
  }
}
```
```python
# main.py
from fastapi import FastAPI, Depends, Header
from fastkit_core.http import success_response
from fastkit_core.i18n import set_locale, _

app = FastAPI()

async def setup_language(accept_language: str = Header(default='en')):
    language = accept_language.split(',')[0].split('-')[0]
    set_locale(language)

@app.get("/", dependencies=[Depends(setup_language)])
def root():
    return {
        "app_name": _('app.name'),
        "title": _('tasks.title')
    }

@app.post("/tasks", dependencies=[Depends(setup_language)])
def create_task(task: dict):
    # Create task logic...
    return success_response(
        data={"id": 1, "title": task['title']},
        message=_('tasks.created', title=task['title'])
    )
```

**Test it:**
```bash
# English
curl http://localhost:8000/
# {"app_name": "Task Manager", "title": "Tasks"}

# Spanish
curl http://localhost:8000/ -H "Accept-Language: es"
# {"app_name": "Gestor de Tareas", "title": "Tareas"}

# Create task in Spanish
curl -X POST http://localhost:8000/tasks \
  -H "Accept-Language: es" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'
# {"message": "Tarea 'Buy milk' creada con éxito", ...}
```

---

## Next Steps

Now that you understand translations, explore:

- **[Validation](validation.md)** - Learn how validation uses translations
- **[Database](database.md)** - Learn about TranslatableMixin for multi-language models
- **[HTTP](http_utilities.md)** - Multilingual API responses
