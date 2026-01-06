"""
Comprehensive tests for FastKit Core Async Services module.

Tests AsyncBaseCrudService with all features:
- Async CRUD operations
- Validation hooks (async)
- Lifecycle hooks (before/after) (async)
- Transaction control (async)
- Error handling
- Pagination
- Bulk operations
- Response schema mapping

"""

import pytest
import pytest_asyncio
from typing import Optional
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from pydantic import BaseModel, EmailStr

from fastkit_core.services import AsyncBaseCrudService
from fastkit_core.database import AsyncRepository


# ============================================================================
# Test Models & Schemas
# ============================================================================

class Base(DeclarativeBase):
    """Base for test models."""
    pass


class User(Base):
    """Test user model."""
    __tablename__ = 'async_users'

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


class UserResponse(BaseModel):
    """User response schema - excludes sensitive data."""
    id: int
    name: str
    email: str
    age: Optional[int] = None
    status: str

    # Pydantic v2 config
    model_config = {'from_attributes': True}


class BasicUserService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
    """Basic async service without custom logic and no response mapping."""
    pass


class UserServiceWithResponse(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
    """Async service with automatic response mapping."""

    def __init__(self, repository):
        super().__init__(repository, response_schema=UserResponse)


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def async_engine():
    """Create in-memory async SQLite engine."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create async database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def repository(async_session):
    """Create async user repository."""
    return AsyncRepository(User, async_session)


@pytest_asyncio.fixture
async def service(repository):
    """Create basic async user service."""
    return BasicUserService(repository)


@pytest_asyncio.fixture
async def service_with_response(repository):
    """Create async user service with response mapping."""
    return UserServiceWithResponse(repository)


@pytest_asyncio.fixture
async def sample_user(service):
    """Create a sample user."""
    user_data = UserCreate(
        name="John Doe",
        email="john@example.com",
        age=30
    )
    return await service.create(user_data)


# ============================================================================
# Test Service Initialization
# ============================================================================

class TestAsyncServiceInit:
    """Test async service initialization."""

    @pytest.mark.asyncio
    async def test_init_with_repository(self, repository):
        """Should initialize with async repository."""
        service = BasicUserService(repository)

        assert service.repository is repository

    @pytest.mark.asyncio
    async def test_service_has_repository_access(self, service):
        """Should have access to repository methods."""
        assert hasattr(service, 'repository')
        assert hasattr(service.repository, 'create')
        assert hasattr(service.repository, 'get')

    @pytest.mark.asyncio
    async def test_service_with_response_schema(self, repository):
        """Should initialize with response schema."""
        service = UserServiceWithResponse(repository)

        assert service.response_schema == UserResponse


# ============================================================================
# Test Helper Methods
# ============================================================================

class TestAsyncHelperMethods:
    """Test async service helper methods."""

    @pytest.mark.asyncio
    async def test_to_dict_with_pydantic_model(self, service):
        """Should convert Pydantic model to dict."""
        user_data = UserCreate(
            name="John Doe",
            email="john@example.com",
            age=30
        )

        result = service._to_dict(user_data)

        assert isinstance(result, dict)
        assert result['name'] == "John Doe"
        assert result['email'] == "john@example.com"
        assert result['age'] == 30

    @pytest.mark.asyncio
    async def test_to_dict_with_dict(self, service):
        """Should handle dict input."""
        data = {'name': 'John', 'email': 'john@example.com'}

        result = service._to_dict(data)

        assert result == data
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_to_dict_exclude_unset(self, service):
        """Should exclude unset values."""
        user_data = UserUpdate(name="John")

        result = service._to_dict(user_data)

        assert 'name' in result
        assert 'email' not in result  # Not set, should be excluded

    @pytest.mark.asyncio
    async def test_to_dict_invalid_type(self, service):
        """Should raise error for invalid type."""
        with pytest.raises(ValueError) as exc_info:
            service._to_dict("invalid_string")

        assert "Cannot convert" in str(exc_info.value)