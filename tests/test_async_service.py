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

# ============================================================================
# Test READ Operations
# ============================================================================

class TestAsyncReadOperations:
    """Test async service read operations."""

    @pytest.mark.asyncio
    async def test_find_by_id(self, service, sample_user):
        """Should find user by ID."""
        found = await service.find(sample_user.id)

        assert found is not None
        assert found.id == sample_user.id
        assert found.name == sample_user.name

    @pytest.mark.asyncio
    async def test_find_nonexistent(self, service):
        """Should return None for nonexistent ID."""
        found = await service.find(9999)

        assert found is None

    @pytest.mark.asyncio
    async def test_find_or_fail_success(self, service, sample_user):
        """Should find user or raise exception."""
        found = await service.find_or_fail(sample_user.id)

        assert found is not None
        assert found.id == sample_user.id

    @pytest.mark.asyncio
    async def test_find_or_fail_raises(self, service):
        """Should raise exception if not found."""
        with pytest.raises(ValueError) as exc_info:
            await service.find_or_fail(9999)

        assert "not found" in str(exc_info.value).lower()
        assert "User" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_all(self, service):
        """Should get all users."""
        # Create multiple users
        for i in range(3):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                age=20 + i
            ))

        users = await service.get_all()

        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_get_all_with_limit(self, service):
        """Should limit results."""
        # Create multiple users
        for i in range(5):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users = await service.get_all(limit=3)

        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_filter_basic(self, service):
        """Should filter users."""
        await service.create(UserCreate(name="Alice", email="alice@example.com", age=25))
        await service.create(UserCreate(name="Bob", email="bob@example.com", age=30))
        await service.create(UserCreate(name="Charlie", email="charlie@example.com", age=25))

        users = await service.filter(age=25)

        assert len(users) == 2
        assert all(u.age == 25 for u in users)

    @pytest.mark.asyncio
    async def test_filter_with_operators(self, service):
        """Should support Django-style operators."""
        await service.create(UserCreate(name="Alice", email="alice@example.com", age=25))
        await service.create(UserCreate(name="Bob", email="bob@example.com", age=30))
        await service.create(UserCreate(name="Charlie", email="charlie@example.com", age=35))

        users = await service.filter(age__gte=30)

        assert len(users) == 2
        assert all(u.age >= 30 for u in users)

    @pytest.mark.asyncio
    async def test_filter_one(self, service):
        """Should get first matching record."""
        await service.create(UserCreate(name="Alice", email="alice@example.com"))
        await service.create(UserCreate(name="Bob", email="bob@example.com"))

        user = await service.filter_one(name="Alice")

        assert user is not None
        assert user.name == "Alice"

    @pytest.mark.asyncio
    async def test_filter_one_not_found(self, service):
        """Should return None if not found."""
        user = await service.filter_one(name="Nonexistent")

        assert user is None

    @pytest.mark.asyncio
    async def test_exists(self, service, sample_user):
        """Should check if record exists."""
        exists = await service.exists(email=sample_user.email)
        not_exists = await service.exists(email="nonexistent@example.com")

        assert exists is True
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_count(self, service):
        """Should count records."""
        for i in range(5):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        count = await service.count()

        assert count == 5

    @pytest.mark.asyncio
    async def test_count_with_filter(self, service):
        """Should count filtered records."""
        await service.create(UserCreate(name="Alice", email="alice@example.com", age=25))
        await service.create(UserCreate(name="Bob", email="bob@example.com", age=30))
        await service.create(UserCreate(name="Charlie", email="charlie@example.com", age=25))

        count = await service.count(age=25)

        assert count == 2

# ============================================================================
# Test CREATE Operations
# ============================================================================

class TestAsyncCreateOperations:
    """Test async create operations."""

    @pytest.mark.asyncio
    async def test_create_basic(self, service):
        """Should create a new record."""
        user_data = UserCreate(
            name="John Doe",
            email="john@example.com",
            age=30
        )

        user = await service.create(user_data)

        assert user.id is not None
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.age == 30

    @pytest.mark.asyncio
    async def test_create_without_commit(self, service):
        """Should create without committing."""
        user_data = UserCreate(
            name="Jane",
            email="jane@example.com"
        )

        user = await service.create(user_data, commit=False)

        # Commit manually
        await service.commit()

        # Verify
        found = await service.find(user.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_create_many(self, service):
        """Should create multiple records."""
        users_data = [
            UserCreate(name=f"User {i}", email=f"user{i}@example.com")
            for i in range(3)
        ]

        users = await service.create_many(users_data)

        assert len(users) == 3
        assert all(u.id is not None for u in users)

    @pytest.mark.asyncio
    async def test_create_with_defaults(self, service):
        """Should use default values."""
        user_data = UserCreate(
            name="Test User",
            email="test@example.com"
        )

        user = await service.create(user_data)

        assert user.status == 'active'  # Default value

# ============================================================================
# Test UPDATE Operations
# ============================================================================

class TestAsyncUpdateOperations:
    """Test async update operations."""

    @pytest.mark.asyncio
    async def test_update_basic(self, service, sample_user):
        """Should update a record."""
        updated = await service.update(
            sample_user.id,
            UserUpdate(name="Jane Doe")
        )

        assert updated is not None
        assert updated.name == "Jane Doe"
        assert updated.id == sample_user.id

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, service):
        """Should return None for nonexistent record."""
        updated = await service.update(9999, UserUpdate(name="Test"))

        assert updated is None

    @pytest.mark.asyncio
    async def test_update_many(self, service):
        """Should update multiple records."""
        # Create users
        for i in range(3):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='pending'
            ))

        # Update all pending
        count = await service.update_many(
            filters={'status': 'pending'},
            data=UserUpdate(status='active')
        )

        assert count == 3

        # Verify
        active_count = await service.count(status='active')
        assert active_count == 3

    @pytest.mark.asyncio
    async def test_update_partial(self, service, sample_user):
        """Should update only provided fields."""
        updated = await service.update(
            sample_user.id,
            UserUpdate(age=31)  # Only age
        )

        assert updated.age == 31
        assert updated.name == sample_user.name  # Unchanged
        assert updated.email == sample_user.email  # Unchanged

# ============================================================================
# Test DELETE Operations
# ============================================================================

class TestAsyncDeleteOperations:
    """Test async delete operations."""

    @pytest.mark.asyncio
    async def test_delete_basic(self, service, sample_user):
        """Should delete a record."""
        deleted = await service.delete(sample_user.id)

        assert deleted is True

        # Verify deleted
        found = await service.find(sample_user.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service):
        """Should return False for nonexistent record."""
        deleted = await service.delete(9999)

        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_many(self, service):
        """Should delete multiple records."""
        # Create users
        for i in range(3):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='inactive'
            ))

        # Delete all inactive
        count = await service.delete_many(filters={'status': 'inactive'})

        assert count == 3

        # Verify
        remaining = await service.count()
        assert remaining == 0
