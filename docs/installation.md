# Installation

- [Requirements](#requirements)
- [Installing FastKit Core](#installing-fastkit-core)
- [Virtual Environment (Recommended)](#virtual-environment)
- [Database Drivers](#database-drivers)
- [Verifying Installation](#verifying-installation)
- [What's Next?](#whats-next)

---

<a name="requirements"></a>
## Requirements

FastKit Core has a few system requirements:

- **Python 3.11 or higher**
- **pip** (Python package manager)

You can verify your Python version:
```bash
python --version
# or
python3 --version
```

> **Note:** While FastKit Core technically supports Python 3.10+, we recommend 
> Python 3.11+ for the best performance and latest language features.

---

<a name="installing-fastkit-core"></a>
## Installing FastKit Core

Install FastKit Core via pip:
```bash
pip install fastkit-core
```

This will install FastKit Core and its core dependencies:

- **FastAPI** (≥0.115) - The web framework
- **Uvicorn** (≥0.34) - ASGI server with standard extras
- **Pydantic** (≥2.10) - Data validation
- **Pydantic Settings** (≥2.6) - Settings management
- **SQLAlchemy** (≥2.0.36) - Database ORM
- **python-dotenv** (≥1.0) - Environment variable management

---

<a name="virtual-environment"></a>
## Virtual Environment (Recommended)

We strongly recommend using a virtual environment to isolate your project 
dependencies:

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver written in Rust.

```bash
# Install uv (if not already installed)
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install FastKit Core
uv add fastkit-core
```

### Using venv (Built-in)
```bash
# Create virtual environment
python -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate

# Install FastKit Core
pip install fastkit-core
```

### Using Poetry
```bash
# Initialize project
poetry init

# Add FastKit Core
poetry add fastkit-core
```

### Using Pipenv
```bash
# Install with Pipenv
pipenv install fastkit-core

# Activate environment
pipenv shell
```

---

<a name="database-drivers"></a>
## Database Drivers

FastKit Core includes SQLAlchemy but **not** database drivers. Install the 
driver for your database:

### PostgreSQL (Recommended)
```bash
pip install psycopg2-binary
```

For production, use the compiled version:
```bash
pip install psycopg2
```

### MySQL/MariaDB
```bash
pip install pymysql
```

Or for better performance:
```bash
pip install mysqlclient
```

### SQLite

SQLite support is built into Python - no additional installation needed!

### Multiple Databases

You can install multiple drivers:
```bash
pip install fastkit-core psycopg2-binary pymysql
```

---

<a name="verifying-installation"></a>
## Verifying Installation

Verify FastKit Core is installed correctly:
```bash
python -c "import fastkit_core; print(fastkit_core.__version__)"
```

You should see the version number, e.g., `0.1.0`

### Quick Test

Create a test file `test_fastkit.py`:
```python
from fastkit_core.config import ConfigManager
from fastkit_core.http import success_response

# Test config
config = ConfigManager(modules=[], auto_load=False)
print("✓ Config module loaded")

# Test responses
response = success_response(data={"status": "working"})
print("✓ HTTP module loaded")
print(f"✓ FastKit Core is ready!")
```

Run it:
```bash
python test_fastkit.py
```

You should see:
```
✓ Config module loaded
✓ HTTP module loaded
✓ FastKit Core is ready!
```

---

<a name="whats-next"></a>
## What's Next?

Now that FastKit Core is installed, you're ready to start building!

### Recommended Next Steps

1. **[Quick Start Guide](/docs/quick-start)**  
   Build your first API in 5 minutes

2. **[Configuration](/docs/configuration)**  
   Set up your environment and database connections

3. **[Database Guide](/docs/database)**  
   Learn the repository pattern and database operations


---

## Troubleshooting

### Import Error: No module named 'fastkit_core'

Make sure you're in the correct virtual environment:
```bash
# Check which Python is active
which python

# Reinstall if needed
pip install --upgrade fastkit-core
```

### SQLAlchemy Import Errors

Install a database driver:
```bash
pip install psycopg2-binary  # PostgreSQL
# or
pip install pymysql          # MySQL
```

### Pydantic Validation Errors

FastKit Core requires Pydantic 2.10+. Upgrade if needed:
```bash
pip install --upgrade pydantic
```

### Still Having Issues?

- Check our [FAQ](/docs/faq)
- Search [GitHub Issues](https://github.com/codevelo-pub/fastkit-core/issues)
- Ask in [GitHub Discussions](https://github.com/codevelo-pub/fastkit-core/discussions)

---

## Development Installation

If you want to contribute or use the latest development version:
```bash
# Clone repository
git clone https://github.com/codevelo-pub/fastkit-core.git
cd fastkit-core

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

See our [Contributing Guide](/docs/contributing) for more details.

---

## Optional Dependencies

FastKit Core has optional features you can install:

### PostgreSQL Support
```bash
pip install "fastkit-core[postgresql]"
```

Includes `psycopg2-binary`

### MySQL Support
```bash
pip install "fastkit-core[mysql]"
```

Includes `pymysql` and `cryptography`

### Full Installation (All Drivers)
```bash
pip install "fastkit-core[full]"
```

### Development Tools
```bash
pip install "fastkit-core[dev]"
```

Includes testing, linting, and documentation tools.

---

## Upgrading FastKit Core

Keep FastKit Core up to date:
```bash
# Upgrade to latest version
pip install --upgrade fastkit-core

# Upgrade to specific version
pip install fastkit-core==0.2.0
```

Always check the [Changelog](/docs/changelog) before upgrading!

---

<a name="requirements-txt"></a>
## Adding to requirements.txt

For reproducible deployments:
```txt
# requirements.txt
fastkit-core>=0.1.0,<1.0.0
psycopg2-binary>=2.9.0
```

Or with extras:
```txt
fastkit-core[postgresql]>=0.1.0,<1.0.0
```

---

## Docker Installation

Using Docker? Here's a sample Dockerfile:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

**Ready to build?** Continue to the [Quick Start Guide](/docs/quick-start) →