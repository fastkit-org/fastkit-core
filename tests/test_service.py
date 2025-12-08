"""
Comprehensive tests for FastKit Core Services module.

Tests BaseCrudService with all features:
- CRUD operations
- Validation hooks
- Lifecycle hooks (before/after)
- Transaction control
- Error handling
- Pagination
- Bulk operations

"""

import pytest
from typing import Optional
from sqlalchemy import create_engine, String, Integer
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, DeclarativeBase
from pydantic import BaseModel, EmailStr, Field

from fastkit_core.services import BaseCrudService
from fastkit_core.database import Repository


# ============================================================================
# Test Models & Schemas
# ============================================================================

class Base(DeclarativeBase):
    """Base for test models."""
    pass


class User(Base):
    """Test user model."""
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='active')


class UserCreate(BaseModel):
    """User creation schema."""
    name: str
    email: EmailStr
    age: Optional[int] = None
    status: str = 'active'


class UserUpdate(BaseModel):
    """User update schema."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = None
    status: Optional[str] = None


class BasicUserService(BaseCrudService[User, UserCreate, UserUpdate]):
    """Basic service without custom logic."""
    pass

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create in-memory SQLite engine."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repository(session):
    """Create user repository."""
    return Repository(User, session)


@pytest.fixture
def service(repository):
    """Create basic user service."""
    return BasicUserService(repository)


@pytest.fixture
def sample_user(service):
    """Create a sample user."""
    user_data = UserCreate(
        name="John Doe",
        email="john@example.com",
        age=30
    )
    return service.create(user_data)


# ============================================================================
# Test Service Initialization
# ============================================================================

class TestServiceInit:
    """Test service initialization."""

    def test_init_with_repository(self, repository):
        """Should initialize with repository."""
        service = BasicUserService(repository)

        assert service.repository is repository

    def test_service_has_repository_access(self, service):
        """Should have access to repository methods."""
        assert hasattr(service, 'repository')
        assert hasattr(service.repository, 'create')
        assert hasattr(service.repository, 'get')
