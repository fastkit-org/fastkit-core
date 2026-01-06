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