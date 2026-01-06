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

# ============================================================================
# Test PAGINATION
# ============================================================================

class TestAsyncPagination:
    """Test async pagination."""

    @pytest.mark.asyncio
    async def test_paginate_basic(self, service):
        """Should paginate results."""
        # Create users
        for i in range(25):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users, meta = await service.paginate(page=1, per_page=10)

        assert len(users) == 10
        assert meta['page'] == 1
        assert meta['per_page'] == 10
        assert meta['total'] == 25
        assert meta['total_pages'] == 3

    @pytest.mark.asyncio
    async def test_paginate_with_filters(self, service):
        """Should paginate with filters."""
        # Create users
        for i in range(20):
            await service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='active' if i % 2 == 0 else 'inactive'
            ))

        users, meta = await service.paginate(
            page=1,
            per_page=5,
            status='active'
        )

        assert len(users) == 5
        assert all(u.status == 'active' for u in users)
        assert meta['total'] == 10  # Only active users

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self, service):
        """Should handle empty results."""
        users, meta = await service.paginate(page=1, per_page=10)

        assert len(users) == 0
        assert meta['total'] == 0
        assert meta['total_pages'] == 0


# ============================================================================
# Test TRANSACTION Management
# ============================================================================

class TestAsyncTransactions:
    """Test async transaction management."""

    @pytest.mark.asyncio
    async def test_commit(self, service):
        """Should commit transaction."""
        user = await service.create(
            UserCreate(name="Test", email="test@example.com"),
            commit=False
        )

        await service.commit()

        # Verify committed
        found = await service.find(user.id)
        assert found is not None

    @pytest.mark.asyncio
    async def test_rollback(self, service):
        """Should rollback transaction."""
        user = await service.create(
            UserCreate(name="Test", email="test@example.com"),
            commit=False
        )

        await service.rollback()

        # Verify rolled back
        count = await service.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_flush(self, service):
        """Should flush changes."""
        user = await service.create(
            UserCreate(name="Test", email="test@example.com"),
            commit=False
        )

        await service.flush()

        # Should have ID after flush
        assert user.id is not None


# ============================================================================
# Test VALIDATION Hooks
# ============================================================================

class TestAsyncValidationHooks:
    """Test async validation hooks."""

    @pytest.mark.asyncio
    async def test_validate_create_hook(self, repository):
        """Should call validate_create hook."""

        class ValidatingService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def validate_create(self, data: UserCreate) -> None:
                if await self.exists(email=data.email):
                    raise ValueError("Email already exists")

        service = ValidatingService(repository)

        # Create first user
        await service.create(UserCreate(name="Alice", email="alice@example.com"))

        # Try to create duplicate
        with pytest.raises(ValueError) as exc_info:
            await service.create(UserCreate(name="Bob", email="alice@example.com"))

        assert "Email already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_update_hook(self, repository, sample_user):
        """Should call validate_update hook."""

        class ValidatingService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def validate_update(self, id, data: UserUpdate) -> None:
                if data.age and data.age < 18:
                    raise ValueError("Age must be 18 or older")

        service = ValidatingService(repository)

        with pytest.raises(ValueError) as exc_info:
            await service.update(sample_user.id, UserUpdate(age=16))

        assert "Age must be 18 or older" in str(exc_info.value)


# ============================================================================
# Test LIFECYCLE Hooks
# ============================================================================

class TestAsyncLifecycleHooks:
    """Test async lifecycle hooks."""

    @pytest.mark.asyncio
    async def test_before_create_hook(self, repository):
        """Should call before_create hook."""

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def before_create(self, data: dict) -> dict:
                data['name'] = data['name'].upper()
                return data

        service = HookService(repository)

        user = await service.create(UserCreate(name="john", email="john@example.com"))

        assert user.name == "JOHN"

    @pytest.mark.asyncio
    async def test_after_create_hook(self, repository):
        """Should call after_create hook."""
        hook_called = []

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def after_create(self, instance: User) -> None:
                hook_called.append(instance.id)

        service = HookService(repository)

        await service.create(UserCreate(name="John", email="john@example.com"))

        assert len(hook_called) == 1

    @pytest.mark.asyncio
    async def test_before_update_hook(self, repository, sample_user):
        """Should call before_update hook."""

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def before_update(self, id, data: dict) -> dict:
                if 'name' in data:
                    data['name'] = data['name'].upper()
                return data

        service = HookService(repository)

        updated = await service.update(sample_user.id, UserUpdate(name="jane"))

        assert updated.name == "JANE"

    @pytest.mark.asyncio
    async def test_after_update_hook(self, repository, sample_user):
        """Should call after_update hook."""
        hook_called = []

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def after_update(self, instance: User) -> None:
                hook_called.append(instance.id)

        service = HookService(repository)

        await service.update(sample_user.id, UserUpdate(name="Jane"))

        assert len(hook_called) == 1

    @pytest.mark.asyncio
    async def test_before_delete_hook(self, repository, sample_user):
        """Should call before_delete hook."""

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def before_delete(self, id) -> None:
                user = await self.find(id)
                if user and user.status == 'active':
                    raise ValueError("Cannot delete active user")

        service = HookService(repository)

        with pytest.raises(ValueError) as exc_info:
            await service.delete(sample_user.id)

        assert "Cannot delete active user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_after_delete_hook(self, repository, sample_user):
        """Should call after_delete hook."""
        hook_called = []

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def after_delete(self, id) -> None:
                hook_called.append(id)

        service = HookService(repository)

        await service.delete(sample_user.id)

        assert len(hook_called) == 1

    @pytest.mark.asyncio
    async def test_hook_execution_order(self, repository):
        """Should execute hooks in correct order."""
        execution_order = []

        class HookService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def validate_create(self, data: UserCreate) -> None:
                execution_order.append('validate')

            async def before_create(self, data: dict) -> dict:
                execution_order.append('before')
                return data

            async def after_create(self, instance: User) -> None:
                execution_order.append('after')

        service = HookService(repository)

        await service.create(UserCreate(name="John", email="john@example.com"))

        assert execution_order == ['validate', 'before', 'after']


# ============================================================================
# Test Response Schema Mapping
# ============================================================================

class TestAsyncResponseSchemaMapping:
    """Test automatic response schema mapping in async service."""

    @pytest.mark.asyncio
    async def test_service_with_response_schema_init(self, repository):
        """Should initialize service with response schema."""
        service = UserServiceWithResponse(repository)

        assert service.response_schema == UserResponse
        assert service.repository is repository

    @pytest.mark.asyncio
    async def test_create_returns_response_schema(self, service_with_response):
        """Should return UserResponse instead of User model."""
        user_data = UserCreate(
            name="John Doe",
            email="john@example.com",
            age=30
        )

        result = await service_with_response.create(user_data)

        assert isinstance(result, UserResponse)
        assert result.id is not None
        assert result.name == "John Doe"

    @pytest.mark.asyncio
    async def test_find_returns_response_schema(self, service_with_response):
        """Should return UserResponse for find."""
        user_data = UserCreate(name="Alice", email="alice@example.com")
        created = await service_with_response.create(user_data)

        found = await service_with_response.find(created.id)

        assert isinstance(found, UserResponse)
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_all_returns_response_schema_list(self, service_with_response):
        """Should return list of UserResponse."""
        for i in range(3):
            await service_with_response.create(
                UserCreate(name=f"User {i}", email=f"user{i}@example.com")
            )

        users = await service_with_response.get_all()

        assert len(users) == 3
        assert all(isinstance(u, UserResponse) for u in users)

    @pytest.mark.asyncio
    async def test_filter_returns_response_schema_list(self, service_with_response):
        """Should return list of UserResponse for filter."""
        await service_with_response.create(
            UserCreate(name="Alice", email="alice@example.com", age=25)
        )
        await service_with_response.create(
            UserCreate(name="Bob", email="bob@example.com", age=30)
        )

        users = await service_with_response.filter(age__gte=25)

        assert len(users) == 2
        assert all(isinstance(u, UserResponse) for u in users)

    @pytest.mark.asyncio
    async def test_paginate_returns_response_schema_list(self, service_with_response):
        """Should return list of UserResponse for paginate."""
        for i in range(10):
            await service_with_response.create(
                UserCreate(name=f"User {i}", email=f"user{i}@example.com")
            )

        users, meta = await service_with_response.paginate(page=1, per_page=5)

        assert len(users) == 5
        assert all(isinstance(u, UserResponse) for u in users)
        assert meta['total'] == 10

    @pytest.mark.asyncio
    async def test_update_returns_response_schema(self, service_with_response):
        """Should return UserResponse for update."""
        user_data = UserCreate(name="David", email="david@example.com")
        created = await service_with_response.create(user_data)

        updated = await service_with_response.update(
            created.id,
            UserUpdate(name="David Updated")
        )

        assert isinstance(updated, UserResponse)
        assert updated.name == "David Updated"

    @pytest.mark.asyncio
    async def test_create_many_returns_response_schema_list(self, service_with_response):
        """Should return list of UserResponse for create_many."""
        users_data = [
            UserCreate(name=f"User {i}", email=f"user{i}@example.com")
            for i in range(3)
        ]

        users = await service_with_response.create_many(users_data)

        assert len(users) == 3
        assert all(isinstance(u, UserResponse) for u in users)


# ============================================================================
# Test Response Schema with Hooks
# ============================================================================

class TestAsyncResponseSchemaWithHooks:
    """Test response schema mapping with async lifecycle hooks."""

    @pytest.mark.asyncio
    async def test_hooks_work_with_response_mapping(self, repository):
        """Should execute hooks and return response schema."""
        hook_log = []

        class HookedService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
            def __init__(self, repo):
                super().__init__(repo, response_schema=UserResponse)

            async def validate_create(self, data: UserCreate) -> None:
                hook_log.append('validate')

            async def before_create(self, data: dict) -> dict:
                hook_log.append('before')
                data['name'] = data['name'].upper()
                return data

            async def after_create(self, instance: User) -> None:
                hook_log.append('after')

        service = HookedService(repository)

        result = await service.create(UserCreate(name="john", email="john@example.com"))

        # Hooks executed
        assert hook_log == ['validate', 'before', 'after']

        # Result is UserResponse
        assert isinstance(result, UserResponse)
        assert result.name == "JOHN"

    @pytest.mark.asyncio
    async def test_validation_error_with_response_mapping(self, repository):
        """Should validate before mapping to response."""

        class ValidatingService(AsyncBaseCrudService[User, UserCreate, UserUpdate, UserResponse]):
            def __init__(self, repo):
                super().__init__(repo, response_schema=UserResponse)

            async def validate_create(self, data: UserCreate) -> None:
                if await self.exists(email=data.email):
                    raise ValueError("Email already exists")

        service = ValidatingService(repository)

        # Create first user
        await service.create(UserCreate(name="Alice", email="alice@example.com"))

        # Try to create duplicate
        with pytest.raises(ValueError) as exc_info:
            await service.create(UserCreate(name="Bob", email="alice@example.com"))

        assert "Email already exists" in str(exc_info.value)

# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestAsyncIntegration:
    """Test real-world async integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self, service):
        """Should handle complete user lifecycle."""
        # Create
        user = await service.create(UserCreate(
            name="John Doe",
            email="john@example.com",
            age=30
        ))
        assert user.id is not None

        # Read
        found = await service.find(user.id)
        assert found.name == "John Doe"

        # Update
        updated = await service.update(user.id, UserUpdate(age=31))
        assert updated.age == 31

        # Delete
        deleted = await service.delete(user.id)
        assert deleted is True

        # Verify deletion
        assert await service.find(user.id) is None

    @pytest.mark.asyncio
    async def test_bulk_operations(self, service):
        """Should handle bulk operations."""
        # Bulk create
        users_data = [
            UserCreate(name=f"User {i}", email=f"user{i}@example.com", status='pending')
            for i in range(10)
        ]
        users = await service.create_many(users_data)
        assert len(users) == 10

        # Bulk update
        updated_count = await service.update_many(
            filters={'status': 'pending'},
            data=UserUpdate(status='active')
        )
        assert updated_count == 10

        # Verify
        active_count = await service.count(status='active')
        assert active_count == 10

        # Bulk delete
        deleted_count = await service.delete_many(filters={'status': 'active'})
        assert deleted_count == 10

    @pytest.mark.asyncio
    async def test_service_with_all_hooks(self, repository):
        """Should work with all hooks together."""
        execution_log = []

        class CompleteService(AsyncBaseCrudService[User, UserCreate, UserUpdate, User]):
            async def validate_create(self, data: UserCreate) -> None:
                execution_log.append('validate_create')
                if await self.exists(email=data.email):
                    raise ValueError("Duplicate email")

            async def before_create(self, data: dict) -> dict:
                execution_log.append('before_create')
                data['name'] = data['name'].upper()
                return data

            async def after_create(self, instance: User) -> None:
                execution_log.append('after_create')

            async def validate_update(self, id, data: UserUpdate) -> None:
                execution_log.append('validate_update')

            async def before_update(self, id, data: dict) -> dict:
                execution_log.append('before_update')
                return data

            async def after_update(self, instance: User) -> None:
                execution_log.append('after_update')

            async def before_delete(self, id) -> None:
                execution_log.append('before_delete')

            async def after_delete(self, id) -> None:
                execution_log.append('after_delete')

        service = CompleteService(repository)

        # Create
        user = await service.create(UserCreate(name="john", email="john@example.com"))
        assert user.name == "JOHN"
        assert 'validate_create' in execution_log
        assert 'before_create' in execution_log
        assert 'after_create' in execution_log

        execution_log.clear()

        # Update
        await service.update(user.id, UserUpdate(age=25))
        assert 'validate_update' in execution_log
        assert 'before_update' in execution_log
        assert 'after_update' in execution_log

        execution_log.clear()

        # Delete
        await service.delete(user.id)
        assert 'before_delete' in execution_log
        assert 'after_delete' in execution_log


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestAsyncEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_update_with_no_changes(self, service, sample_user):
        """Should handle update with no changes."""
        updated = await service.update(sample_user.id, UserUpdate())

        assert updated is not None

    @pytest.mark.asyncio
    async def test_pagination_beyond_last_page(self, service):
        """Should handle page beyond total pages."""
        await service.create(UserCreate(name="User", email="user@example.com"))

        users, meta = await service.paginate(page=100, per_page=10)

        assert len(users) == 0
        assert meta['page'] == 100

    @pytest.mark.asyncio
    async def test_count_with_no_records(self, service):
        """Should return 0 for empty table."""
        count = await service.count()

        assert count == 0

    @pytest.mark.asyncio
    async def test_filter_with_no_matches(self, service, sample_user):
        """Should return empty list when no matches."""
        users = await service.filter(name="Nonexistent")

        assert users == []