# Configuration

- [Introduction](#introduction)
- [Quick Example](#quick-example)
- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [Accessing Configuration](#accessing-configuration)
- [Multiple Environments](#multiple-environments)
- [Configuration Caching](#configuration-caching)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

---

<a name="introduction"></a>
## Introduction

FastKit Core's configuration system provides a flexible, environment-aware way to manage 
your application settings. It combines the simplicity of Python modules with the power 
of environment variables.

**Key Features:**

- ✅ **Python-based** - Configuration files are just Python modules
- ✅ **Environment Variables** - Override any config with `.env` files
- ✅ **Multiple Instances** - Different configs for dev, test, production
- ✅ **Auto-discovery** - Automatically finds `.env` files
- ✅ **Type Casting** - Automatic conversion of environment variables
- ✅ **Zero Dependencies** - Uses only Python's standard library + `python-dotenv`

---

<a name="quick-example"></a>
## Quick Example

**Create a config file:**
```python
# config/app.py
import os

APP_NAME = os.getenv('APP_NAME', 'My FastKit App')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
VERSION = '1.0.0'
```

**Load and use:**
```python
from fastkit_core.config import config

# Access configuration
app_name = config('app.APP_NAME')  # "My FastKit App"
debug = config('app.DEBUG')        # False
version = config('app.VERSION')    # "1.0.0"
```

That's it! FastKit Core handles the rest.

---

<a name="configuration-files"></a>
## Configuration Files

### Directory Structure

By default, FastKit Core looks for configuration modules in a `config/` directory:
```
your-project/
├── config/
│   ├── __init__.py      # Makes it a Python package
│   ├── app.py           # Application settings
│   ├── database.py      # Database connections
│   ├── cache.py         # Cache configuration
│   └── services.py      # External services
├── .env                 # Environment variables
├── .env.example         # Template for .env
└── main.py
```

### Creating Configuration Files

Configuration files are regular Python modules:
```python
# config/app.py
import os

# Application name
APP_NAME = os.getenv('APP_NAME', 'FastKit App')

# Debug mode
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# API settings
API_VERSION = 'v1'
API_PREFIX = '/api/v1'

# CORS settings
ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
]

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
```

**Rules:**
- Use `UPPER_CASE` for configuration values
- Use `os.getenv()` for values that should come from environment
- Provide sensible defaults
- Keep secrets in environment variables, not in code

---

<a name="environment-variables"></a>
## Environment Variables

### Creating .env Files

Environment variables are loaded from `.env` files:
```bash
# .env
APP_NAME=My Production App
DEBUG=False
SECRET_KEY=your-secret-key-here

# Database
DB_DRIVER=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
DB_USERNAME=postgres
DB_PASSWORD=secret

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Auto-discovery

FastKit Core automatically searches for `.env` files:
```
1. Current directory (.env)
2. Parent directory (../.env)
3. Grandparent directory (../../.env)
... continues up to root
```

**Best Practice:** Keep `.env` in your project root.

### Environment Variable Priority

Environment variables **always override** configuration files:
```python
# config/app.py
APP_NAME = 'Default Name'  # Fallback value

# .env
APP_NAME="Production App"    # This wins!

# Result
config('app.APP_NAME')  # "Production App"
```

### Type Casting

FastKit Core automatically converts environment variable strings:
```python
# .env
DEBUG=true
PORT=8000
RATE_LIMIT=100.5

# Automatic conversion
config('app.DEBUG')       # bool: True
config('app.PORT')        # int: 8000
config('app.RATE_LIMIT')  # float: 100.5
```

**Supported conversions:**
- `"true"`, `"yes"`, `"1"` → `True`
- `"false"`, `"no"`, `"0"` → `False`
- `"123"` → `123` (int)
- `"123.45"` → `123.45` (float)
- Everything else → string

---

<a name="accessing-configuration"></a>
## Accessing Configuration

### Using Convenience Functions

The simplest way to access configuration:
```python
from fastkit_core.config import config, config_all, config_has

# Get a value
app_name = config('app.APP_NAME')

# With default value
api_key = config('app.API_KEY', default='not-set')

# Check if key exists
if config_has('app.SECRET_KEY'):
    secret = config('app.SECRET_KEY')

# Get all config
all_config = config_all()
```

### Using ConfigManager Directly

For more control, use `ConfigManager`:
```python
from fastkit_core.config import ConfigManager

# Create manager
config_manager = ConfigManager()

# Access values
app_name = config_manager.get('app.APP_NAME')
debug = config_manager.get('app.DEBUG', default=False)

# Set values (for testing)
config_manager.set('app.TEST_MODE', True)

# Check existence
has_db = config_manager.has('database.CONNECTIONS')

# Get entire module
app_config = config_manager.get('app')  # Returns dict
```

### Dot Notation

Use dot notation to access nested configuration:
```python
# Format: 'module.KEY'
app_name = config('app.APP_NAME')
db_host = config('database.HOST')
cache_ttl = config('cache.DEFAULT_TTL')
```

---

<a name="multiple-environments"></a>
## Multiple Environments

### Per-Environment Configuration

Create different configuration instances:
```python
from fastkit_core.config import ConfigManager

# Development
dev_config = ConfigManager(env_file='.env.development')

# Testing
test_config = ConfigManager(env_file='.env.test')

# Production
prod_config = ConfigManager(env_file='.env.production')
```

### Environment-Specific Files
```
your-project/
├── .env                 # Default/shared
├── .env.development     # Development overrides
├── .env.test           # Test environment
├── .env.production     # Production settings
└── .env.example        # Template (commit this)
```

**Example .env files:**
```bash
# .env.development
DEBUG=True
DB_HOST=localhost
DB_NAME=myapp_dev

# .env.test
DEBUG=False
DB_NAME=myapp_test

# .env.production
DEBUG=False
DB_HOST=prod-db.example.com
DB_NAME=myapp_prod
```

### Switching Environments

Use an environment variable to select config:
```python
# config/__init__.py
import os
from fastkit_core.config import ConfigManager

ENV = os.getenv('APP_ENV', 'development')

config_manager = ConfigManager(env_file=f'.env.{ENV}')
```

Then run with:
```bash
# Development (default)
uvicorn main:app --reload

# Testing
APP_ENV=test pytest

# Production
APP_ENV=production uvicorn main:app --workers 4
```

### Testing with Custom Config

Override configuration in tests:
```python
# tests/conftest.py
import pytest
from fastkit_core.config import ConfigManager, set_config_manager

@pytest.fixture
def test_config():
    """Create isolated test configuration."""
    config = ConfigManager(
        modules=['app', 'database'],
        env_file='.env.test',
        auto_load=True
    )
    
    # Override specific values
    config.set('app.DEBUG', False)
    config.set('database.CONNECTIONS', {
        'default': {
            'url': 'sqlite:///:memory:'
        }
    })
    
    # Set as global config
    set_config_manager(config)
    
    yield config
    
    # Cleanup (optional)
    set_config_manager(None)
```

---

<a name="configuration-caching"></a>
## Configuration Caching

### Loading Configuration

Configuration is loaded once and cached:
```python
from fastkit_core.config import ConfigManager

# First load - reads files
config = ConfigManager()  # Loads config modules

# Subsequent access - cached
value1 = config.get('app.APP_NAME')  # Fast
value2 = config.get('app.DEBUG')     # Fast
```

### Reloading Configuration

Reload if configuration files change:
```python
from fastkit_core.config import config_reload

# Reload all configuration
config_reload()

# Or reload specific manager
config_manager.reload()
```

**When to reload:**
- During development (auto-reload with `--reload`)
- After updating `.env` file
- In tests between test cases

---

<a name="best-practices"></a>
## Best Practices

### 1. Keep Secrets in Environment Variables

❌ **Bad:**
```python
# config/app.py
SECRET_KEY = 'my-secret-key-123'  # NEVER DO THIS!
```

✅ **Good:**
```python
# config/app.py
SECRET_KEY = os.getenv('SECRET_KEY')

# Validate it exists
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
```

### 2. Provide Sensible Defaults

✅ **Good:**
```python
# config/app.py
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
PORT = int(os.getenv('PORT', 8000))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

### 3. Group Related Settings
```python
# config/database.py
import os

CONNECTIONS = {
    'default': {
        'driver': os.getenv('DB_DRIVER', 'postgresql'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'myapp'),
        'username': os.getenv('DB_USERNAME', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
    }
}
```

### 4. Document Your Configuration
```python
# config/app.py
"""
Application Configuration

Environment Variables:
    APP_NAME: Application name (default: "FastKit App")
    DEBUG: Enable debug mode (default: False)
    SECRET_KEY: Secret key for sessions (REQUIRED)
    ALLOWED_HOSTS: Comma-separated list of allowed hosts
"""

APP_NAME = os.getenv('APP_NAME', 'FastKit App')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY')  # Required!

# Parse comma-separated list
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
```

### 5. Create .env.example
```bash
# .env.example
# Copy this to .env and fill in your values

# Application
APP_NAME=My App
DEBUG=False
SECRET_KEY=

# Database
DB_DRIVER=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
DB_USERNAME=postgres
DB_PASSWORD=

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 6. Validate Required Settings
```python
# config/app.py
import os

SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Validate in production
if not os.getenv('DEBUG', 'False').lower() == 'true':
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in production")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set in production")
```

### 7. Use Type Hints
```python
# config/app.py
from typing import List

APP_NAME: str = os.getenv('APP_NAME', 'FastKit App')
DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
PORT: int = int(os.getenv('PORT', 8000))
ALLOWED_ORIGINS: List[str] = ['http://localhost:3000']
```

---

<a name="api-reference"></a>
## API Reference

### ConfigManager Class
```python
class ConfigManager:
    """Configuration manager with environment-specific support."""
    
    def __init__(
        self,
        modules: list[str] | None = None,
        config_package: str = 'config',
        env_file: str | Path | None = None,
        auto_load: bool = True
    ) -> None:
        """
        Initialize configuration manager.
        
        Args:
            modules: Config modules to load (default: ['app', 'database', 'cache'])
            config_package: Package containing config modules (default: 'config')
            env_file: Path to .env file (default: auto-discover)
            auto_load: Load config immediately (default: True)
        """
```

#### Methods

**`get(key_path: str, default: Any = None) -> Any`**

Get configuration value using dot notation.
```python
# Get value
app_name = config_manager.get('app.APP_NAME')

# With default
api_key = config_manager.get('app.API_KEY', default='not-set')

# Get entire module
app_config = config_manager.get('app')
```

**`set(key_path: str, value: Any) -> None`**

Set configuration value at runtime.
```python
config_manager.set('app.TEST_MODE', True)
config_manager.set('database.CONNECTION', {...})
```

**`has(key_path: str) -> bool`**

Check if configuration key exists.
```python
if config_manager.has('app.SECRET_KEY'):
    secret = config_manager.get('app.SECRET_KEY')
```

**`all() -> dict[str, dict[str, Any]]`**

Get all configuration data.
```python
all_config = config_manager.all()
# Returns: {
#     'app': {'APP_NAME': '...', 'DEBUG': False},
#     'database': {'CONNECTIONS': {...}}
# }
```

**`reload() -> None`**

Reload all configuration from files.
```python
config_manager.reload()
```

**`load() -> None`**

Manually load configuration (called automatically if `auto_load=True`).
```python
config_manager.load()
```

---

### Convenience Functions

**`config(key_path: str, default: Any = None) -> Any`**

Get configuration from default manager.
```python
from fastkit_core.config import config

app_name = config('app.APP_NAME')
debug = config('app.DEBUG', default=False)
```

**`config_set(key_path: str, value: Any) -> None`**

Set configuration in default manager.
```python
from fastkit_core.config import config_set

config_set('app.TEST_MODE', True)
```

**`config_has(key_path: str) -> bool`**

Check if key exists in default manager.
```python
from fastkit_core.config import config_has

if config_has('app.SECRET_KEY'):
    secret = config('app.SECRET_KEY')
```

**`config_all() -> dict[str, dict[str, Any]]`**

Get all configuration from default manager.
```python
from fastkit_core.config import config_all

all_config = config_all()
```

**`config_reload() -> None`**

Reload default manager configuration.
```python
from fastkit_core.config import config_reload

config_reload()
```

---

### Global Manager Functions

**`get_config_manager() -> ConfigManager`**

Get the default global configuration manager.
```python
from fastkit_core.config import get_config_manager

manager = get_config_manager()
```

**`set_config_manager(manager: ConfigManager) -> None`**

Set a custom global configuration manager.
```python
from fastkit_core.config import ConfigManager, set_config_manager

# Create custom manager
custom_config = ConfigManager(env_file='.env.test')

# Set as global
set_config_manager(custom_config)
```

---

## Complete Example

Here's a complete configuration setup:
```python
# config/app.py
import os

# Application
APP_NAME = os.getenv('APP_NAME', 'FastKit App')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
VERSION = '1.0.0'

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY and not DEBUG:
    raise ValueError("SECRET_KEY is required in production")

# API
API_PREFIX = '/api/v1'
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# CORS
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else [
    'http://localhost:3000',
    'http://localhost:8080',
]
```
```python
# config/database.py
import os

CONNECTIONS = {
    'default': {
        'driver': os.getenv('DB_DRIVER', 'postgresql'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'myapp'),
        'username': os.getenv('DB_USERNAME', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20)),
        'echo': os.getenv('DB_ECHO', 'False').lower() == 'true',
    }
}
```
```python
# main.py
from fastapi import FastAPI
from fastkit_core.config import config

app = FastAPI(
    title=config('app.APP_NAME'),
    version=config('app.VERSION'),
    debug=config('app.DEBUG')
)

@app.get("/")
def root():
    return {
        "app": config('app.APP_NAME'),
        "version": config('app.VERSION'),
        "debug": config('app.DEBUG')
    }
```
```bash
# .env
APP_NAME=My Awesome API
DEBUG=True
SECRET_KEY=dev-secret-key

DB_DRIVER=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp_dev
DB_USERNAME=postgres
DB_PASSWORD=postgres
```

---

## Next Steps

Now that you understand configuration, learn about:

- **[Database](/docs/database)** - Configure multiple database connections
- **[Services](/docs/services)** - Use config in your service layer
