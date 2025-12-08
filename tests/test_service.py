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

# ============================================================================
# Test Helper Methods
# ============================================================================

class TestHelperMethods:
    """Test service helper methods."""

    def test_to_dict_with_pydantic_model(self, service):
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

    def test_to_dict_with_dict(self, service):
        """Should handle dict input."""
        data = {'name': 'John', 'email': 'john@example.com'}

        result = service._to_dict(data)

        assert result == data
        assert isinstance(result, dict)

    def test_to_dict_exclude_unset(self, service):
        """Should exclude unset values."""
        user_data = UserUpdate(name="John")

        result = service._to_dict(user_data)

        assert 'name' in result
        assert 'email' not in result  # Not set, should be excluded
        assert 'age' not in result

    def test_to_dict_invalid_type(self, service):
        """Should raise error for invalid type."""
        with pytest.raises(ValueError) as exc_info:
            service._to_dict("invalid_string")

        assert "Cannot convert" in str(exc_info.value)

# ============================================================================
# Test READ Operations
# ============================================================================

class TestReadOperations:
    """Test service read operations."""

    def test_find_by_id(self, service, sample_user):
        """Should find user by ID."""
        found = service.find(sample_user.id)

        assert found is not None
        assert found.id == sample_user.id
        assert found.name == sample_user.name

    def test_find_nonexistent(self, service):
        """Should return None for nonexistent ID."""
        found = service.find(9999)

        assert found is None

    def test_find_or_fail_success(self, service, sample_user):
        """Should find user or raise exception."""
        found = service.find_or_fail(sample_user.id)

        assert found is not None
        assert found.id == sample_user.id

    def test_find_or_fail_raises(self, service):
        """Should raise exception if not found."""
        with pytest.raises(ValueError) as exc_info:
            service.find_or_fail(9999)

        assert "not found" in str(exc_info.value).lower()
        assert "User" in str(exc_info.value)

    def test_get_all(self, service):
        """Should get all users."""
        # Create multiple users
        for i in range(3):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                age=20 + i
            ))

        users = service.get_all()

        assert len(users) == 3

    def test_get_all_with_limit(self, service):
        """Should limit results."""
        # Create multiple users
        for i in range(5):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users = service.get_all(limit=3)

        assert len(users) == 3

    def test_filter_basic(self, service):
        """Should filter users."""
        service.create(UserCreate(name="Alice", email="alice@example.com", age=25))
        service.create(UserCreate(name="Bob", email="bob@example.com", age=30))
        service.create(UserCreate(name="Charlie", email="charlie@example.com", age=25))

        users = service.filter(age=25)

        assert len(users) == 2
        assert all(u.age == 25 for u in users)

    def test_filter_with_operators(self, service):
        """Should support Django-style operators."""
        service.create(UserCreate(name="User1", email="user1@example.com", age=20))
        service.create(UserCreate(name="User2", email="user2@example.com", age=30))
        service.create(UserCreate(name="User3", email="user3@example.com", age=40))

        users = service.filter(age__gte=30)

        assert len(users) == 2
        assert all(u.age >= 30 for u in users)

    def test_filter_with_limit(self, service):
        """Should limit filter results."""
        for i in range(5):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='active'
            ))

        users = service.filter(status='active', _limit=3)

        assert len(users) == 3

    def test_filter_with_offset(self, service):
        """Should offset filter results."""
        for i in range(5):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users = service.filter(_offset=2, _limit=2)

        assert len(users) == 2

    def test_filter_with_order_by(self, service):
        """Should order filter results."""
        service.create(UserCreate(name="Charlie", email="charlie@example.com", age=30))
        service.create(UserCreate(name="Alice", email="alice@example.com", age=25))
        service.create(UserCreate(name="Bob", email="bob@example.com", age=35))

        users = service.filter(_order_by='age')

        assert users[0].age == 25
        assert users[1].age == 30
        assert users[2].age == 35

    def test_filter_with_order_by_desc(self, service):
        """Should order descending."""
        service.create(UserCreate(name="User1", email="user1@example.com", age=25))
        service.create(UserCreate(name="User2", email="user2@example.com", age=35))
        service.create(UserCreate(name="User3", email="user3@example.com", age=30))

        users = service.filter(_order_by='-age')

        assert users[0].age == 35
        assert users[1].age == 30
        assert users[2].age == 25

    def test_filter_one(self, service):
        """Should get first matching record."""
        service.create(UserCreate(name="Alice", email="alice@example.com", age=25))
        service.create(UserCreate(name="Bob", email="bob@example.com", age=25))

        user = service.filter_one(age=25)

        assert user is not None
        assert user.age == 25

    def test_filter_one_not_found(self, service):
        """Should return None if not found."""
        user = service.filter_one(age=999)

        assert user is None

    def test_exists(self, service, sample_user):
        """Should check if record exists."""
        assert service.exists(email=sample_user.email) is True
        assert service.exists(email="nonexistent@example.com") is False

    def test_count(self, service):
        """Should count records."""
        for i in range(5):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='active'
            ))

        count = service.count(status='active')

        assert count == 5

    def test_count_with_filters(self, service):
        """Should count with filters."""
        service.create(UserCreate(name="User1", email="user1@example.com", age=25))
        service.create(UserCreate(name="User2", email="user2@example.com", age=30))
        service.create(UserCreate(name="User3", email="user3@example.com", age=25))

        count = service.count(age=25)

        assert count == 2

# ============================================================================
# Test Pagination
# ============================================================================

class TestPagination:
    """Test pagination functionality."""

    def test_paginate_first_page(self, service):
        """Should paginate first page."""
        for i in range(25):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users, meta = service.paginate(page=1, per_page=10)

        assert len(users) == 10
        assert meta['page'] == 1
        assert meta['per_page'] == 10
        assert meta['total'] == 25
        assert meta['total_pages'] == 3
        assert meta['has_next'] is True
        assert meta['has_prev'] is False

    def test_paginate_second_page(self, service):
        """Should paginate second page."""
        for i in range(25):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users, meta = service.paginate(page=2, per_page=10)

        assert len(users) == 10
        assert meta['page'] == 2
        assert meta['has_next'] is True
        assert meta['has_prev'] is True

    def test_paginate_last_page(self, service):
        """Should handle last page correctly."""
        for i in range(25):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com"
            ))

        users, meta = service.paginate(page=3, per_page=10)

        assert len(users) == 5
        assert meta['page'] == 3
        assert meta['has_next'] is False
        assert meta['has_prev'] is True

    def test_paginate_with_filters(self, service):
        """Should paginate with filters."""
        for i in range(30):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='active' if i % 2 == 0 else 'inactive'
            ))

        users, meta = service.paginate(page=1, per_page=5, status='active')

        assert len(users) == 5
        assert all(u.status == 'active' for u in users)
        assert meta['total'] == 15  # Half are active

# ============================================================================
# Test CREATE Operations
# ============================================================================
class TestCreateOperations:
    """Test service create operations."""

    def test_create_basic(self, service):
        """Should create user."""
        user_data = UserCreate(
            name="John Doe",
            email="john@example.com",
            age=30
        )

        user = service.create(user_data)

        assert user.id is not None
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.age == 30

    def test_create_with_dict(self, service):
        """Should create from dict."""
        user_data = {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'age': 25
        }

        user = service.create(user_data)

        assert user.id is not None
        assert user.name == "Jane Doe"

    def test_create_without_optional_fields(self, service):
        """Should create without optional fields."""
        user_data = UserCreate(
            name="John Doe",
            email="john@example.com"
        )

        user = service.create(user_data)

        assert user.id is not None
        assert user.age is None

    def test_create_with_commit_false(self, service, session):
        """Should not commit when commit=False."""
        user_data = UserCreate(
            name="John Doe",
            email="john@example.com"
        )

        user = service.create(user_data, commit=False)

        # Rollback
        session.rollback()

        # Should not exist after rollback
        found = service.find(user.id)
        assert found is None

    def test_create_many(self, service):
        """Should create multiple users."""
        users_data = [
            UserCreate(name=f"User {i}", email=f"user{i}@example.com")
            for i in range(3)
        ]

        users = service.create_many(users_data)

        assert len(users) == 3
        assert all(u.id is not None for u in users)

    def test_create_many_with_commit_false(self, service, session):
        """Should not commit bulk create when commit=False."""
        users_data = [
            UserCreate(name=f"User {i}", email=f"user{i}@example.com")
            for i in range(3)
        ]

        users = service.create_many(users_data, commit=False)

        # Rollback
        session.rollback()

        # Should not exist
        count = service.count()
        assert count == 0

# ============================================================================
# Test UPDATE Operations
# ============================================================================
class TestUpdateOperations:
    """Test service update operations."""

    def test_update_basic(self, service, sample_user):
        """Should update user."""
        update_data = UserUpdate(name="Jane Doe")

        updated = service.update(sample_user.id, update_data)

        assert updated is not None
        assert updated.name == "Jane Doe"
        assert updated.email == sample_user.email  # Unchanged

    def test_update_multiple_fields(self, service, sample_user):
        """Should update multiple fields."""
        update_data = UserUpdate(name="Jane Doe", age=35)

        updated = service.update(sample_user.id, update_data)

        assert updated.name == "Jane Doe"
        assert updated.age == 35

    def test_update_nonexistent(self, service):
        """Should return None for nonexistent record."""
        update_data = UserUpdate(name="Nobody")

        updated = service.update(9999, update_data)

        assert updated is None

    def test_update_with_commit_false(self, service, sample_user, session):
        """Should not commit when commit=False."""
        original_name = sample_user.name
        update_data = UserUpdate(name="Changed")

        service.update(sample_user.id, update_data, commit=False)

        # Rollback
        session.rollback()

        # Should be unchanged
        found = service.find(sample_user.id)
        assert found.name == original_name

    def test_update_many(self, service):
        """Should update multiple records."""
        # Create users
        for i in range(5):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='active'
            ))

        # Update all active users
        update_data = UserUpdate(status='inactive')
        count = service.update_many(
            filters={'status': 'active'},
            data=update_data
        )

        assert count == 5

        # Verify
        inactive_count = service.count(status='inactive')
        assert inactive_count == 5
