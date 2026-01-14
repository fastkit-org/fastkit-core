# Contributing to FastKit Core

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

---

<a name="getting-started"></a>
## Getting Started

Thank you for your interest in contributing to FastKit Core! This document will guide you through the process.

### Understanding the Project

FastKit Core is a lightweight toolkit that adds structure and common patterns to FastAPI. Before contributing, we recommend:

1. **Read the documentation**
   - [Quick Start Guide](/docs/quick_start.md)
   - [Database Guide](/docs/database.md)
   - [Services Guide](/docs/services.md)

2. **Understand the core architecture**
   - Repository Pattern
   - Service Layer
   - Validation
   - HTTP Utilities

3. **Explore the codebase**
   - Browse [fastkit_core](../fastkit_core/) source code
   - Check [tests](../tests/) to see how tests are written

### Ways to Contribute

You can contribute in several ways:

1. **Report bugs** - Submit issues for problems you find
2. **Suggest features** - Propose new functionality
3. **Submit code** - Fix bugs or implement new features
4. **Improve documentation** - Enhance existing documentation
5. **Help others** - Answer questions in GitHub Issues

---

<a name="development-setup"></a>
## Development Setup

### Fork and Clone

```bash
# 1. Fork the repository on GitHub
# Visit https://github.com/codevelo-pub/fastkit-core and click the Fork button

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/fastkit-core.git
cd fastkit-core

# 3. Add the upstream repository
git remote add upstream https://github.com/codevelo-pub/fastkit-core.git

# 4. Verify the remotes
git remote -v
```

### Setting Up Development Environment

#### Option 1: Using uv (Recommended)

```bash
# Install uv (if not already installed)
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

#### Option 2: Using pip

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

#### Option 3: Using Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with dev
```

### Verify Setup

```bash
# Run tests to ensure everything works
pytest

# Run linting
ruff check fastkit_core

# Format code
black fastkit_core
```

---

<a name="making-changes"></a>
## Making Changes

### Branch Naming Convention

```bash
# Update main branch
git checkout main
git pull upstream main

# Create a new branch (use meaningful prefixes)
git checkout -b feature/your-feature-name
git checkout -b fix/your-bug-fix
git checkout -b docs/your-documentation-update
git checkout -b refactor/your-refactoring
```

**Examples:**
- `feature/add-soft-delete-mixin`
- `fix/repository-pagination-bug`
- `docs/update-api-examples`
- `refactor/simplify-validation-layer`

### Making Changes

1. **Code quality principles**
   - Write clear, readable code
   - Add type hints
   - Write docstrings
   - Keep code simple and focused

2. **Commit message format**
   ```bash
   # Good commit message format
   git commit -m "feat: add TranslatableMixin to models"
   git commit -m "fix: resolve pagination offset bug"
   git commit -m "docs: update installation guide"
   ```

3. **Before committing**
   ```bash
   # Format code
   black fastkit_core tests

   # Sort imports
   isort fastkit_core tests

   # Run linter
   ruff check fastkit_core tests

   # Run tests
   pytest

   # Type checking (optional)
   mypy fastkit_core
   ```

### Commit Message Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

**Format:** `<type>(<scope>): <subject>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no functionality change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test-related changes
- `chore`: Build/process/tooling changes

**Examples:**
```bash
feat(repository): add support for bulk operations
fix(validation): handle None values in custom validators
docs(installation): add uv installation instructions
test(database): add tests for soft delete mixin
```

---

<a name="testing"></a>
## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific file
pytest tests/test_repository.py

# Run specific test
pytest tests/test_repository.py::test_filter_by_id

# With coverage report
pytest --cov=fastkit_core --cov-report=html

# View HTML coverage report
# Open htmlcov/index.html
```

### Writing Tests

1. **Test file location**
   ```
   fastkit_core/
       repository.py
   tests/
       test_repository.py
   ```

2. **Test example**
   ```python
   import pytest
   from fastkit_core.database import Repository

   class TestRepository:
       def test_create_instance(self, db_session):
           """Test creating a new instance"""
           repo = Repository(User, db_session)
           user = repo.create(email="test@example.com", name="Test")
           assert user.id is not None
           assert user.email == "test@example.com"

       def test_filter_by_id(self, db_session):
           """Test filtering by ID"""
           repo = Repository(User, db_session)
           user = repo.create(email="test@example.com", name="Test")
           found = repo.find(user.id)
           assert found is not None
           assert found.id == user.id
   ```

3. **Testing principles**
   - Tests should be fast
   - Tests should be independent (don't depend on other tests)
   - Use descriptive test names
   - One test should test one thing
   - Use fixtures to reduce duplication

### Test Coverage

We aim for high test coverage:

```bash
# Check coverage
pytest --cov=fastkit_core --cov-report=term-missing

# Target: > 80% coverage for new code
```

---

<a name="code-style"></a>
## Code Style

FastKit Core uses the following tools to ensure code quality:

### Linting with Ruff

```bash
# Check for code issues
ruff check fastkit_core tests

# Auto-fix fixable issues
ruff check --fix fastkit_core tests
```

### Formatting with Black

```bash
# Format code
black fastkit_core tests

# Check formatting
black --check fastkit_core tests
```

### Import Sorting with isort

```bash
# Sort imports
isort fastkit_core tests

# Check imports
isort --check-only fastkit_core tests
```

### Type Checking with mypy

```bash
# Run type checker
mypy fastkit_core
```

### Pre-commit Hook (Optional)

Install pre-commit hooks to automatically check code:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-requests]
```

---

<a name="submitting-changes"></a>
## Submitting Changes

### Pull Request Process

1. **Ensure your branch is up to date**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Push to your fork**
   ```bash
   git push origin your-branch
   ```

3. **Create a Pull Request**
   - Visit https://github.com/codevelo-pub/fastkit-core
   - Click "Compare & pull request"
   - Fill out the PR template

### Pull Request Template

```markdown
## Description
Brief description of your changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issue
Fixes #issue_number

## How Has This Been Tested?
Please describe your test scenarios:
- [ ] Test scenario 1
- [ ] Test scenario 2
- [ ] Test scenario 3

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings
- [ ] All tests pass
```

### PR Review Process

1. **Automated Checks**
   - CI will automatically run tests
   - Ensure all checks pass

2. **Code Review**
   - Maintainers will review your code
   - They may request changes
   - Respond promptly and professionally

3. **Merge**
   - Once approved, your PR will be merged into main
   - Changes will be included in the next release

---

<a name="release-process"></a>
## Release Process

### Version Numbering

FastKit Core follows [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

Example: `0.3.2` → `0.4.0`

### Release Steps (Maintainers Only)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag -a v0.4.0 -m "Release v0.4.0"`
4. Push tag: `git push upstream v0.4.0`
5. GitHub Actions will automatically publish to PyPI

---

## Getting Help

### Resources

- **Documentation**: [docs/README.md](/docs/README.md)
- **GitHub Issues**: [Report bugs or ask questions](https://github.com/codevelo-pub/fastkit-core/issues)

### Contact

- **Email**: info@codevelo.io
- **Website**: https://codevelo.io

---

**Thank you for your contribution!** 🎉

Every contribution matters, no matter how big or small. Let's build a better FastAPI development experience together!
