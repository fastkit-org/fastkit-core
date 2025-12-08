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

# ============================================================================
# Test DELETE Operations
# ============================================================================
class TestDeleteOperations:
    """Test service delete operations."""

    def test_delete_basic(self, service, sample_user):
        """Should delete user."""
        user_id = sample_user.id

        deleted = service.delete(user_id)

        assert deleted is True

        # Verify
        found = service.find(user_id)
        assert found is None

    def test_delete_nonexistent(self, service):
        """Should return False for nonexistent record."""
        deleted = service.delete(9999)

        assert deleted is False

    def test_delete_with_commit_false(self, service, sample_user, session):
        """Should not commit when commit=False."""
        user_id = sample_user.id

        service.delete(user_id, commit=False)

        # Rollback
        session.rollback()

        # Should still exist
        found = service.find(user_id)
        assert found is not None

    def test_delete_many(self, service):
        """Should delete multiple records."""
        # Create users
        for i in range(5):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                status='inactive'
            ))

        # Delete inactive users
        count = service.delete_many(filters={'status': 'inactive'})

        assert count == 5

        # Verify
        remaining = service.count()
        assert remaining == 0

# ============================================================================
# Test Validation Hooks
# ============================================================================
class TestValidationHooks:
    """Test validation hooks."""

    def test_validate_create_hook(self, repository):
        """Should call validate_create hook."""

        class ValidatingService(BaseCrudService[User, UserCreate, UserUpdate]):
            def validate_create(self, data: UserCreate) -> None:
                if self.exists(email=data.email):
                    raise ValueError("Email already exists")

        service = ValidatingService(repository)

        # First user - OK
        user1 = service.create(UserCreate(
            name="User1",
            email="test@example.com"
        ))

        # Duplicate email - should fail
        with pytest.raises(ValueError) as exc_info:
            service.create(UserCreate(
                name="User2",
                email="test@example.com"
            ))

        assert "Email already exists" in str(exc_info.value)

    def test_validate_update_hook(self, repository, sample_user):
        """Should call validate_update hook."""

        class ValidatingService(BaseCrudService[User, UserCreate, UserUpdate]):
            def validate_update(self, id, data: UserUpdate) -> None:
                if data.age and data.age < 18:
                    raise ValueError("Age must be 18 or older")

        service = ValidatingService(repository)

        # Valid update
        service.update(sample_user.id, UserUpdate(age=25))

        # Invalid update
        with pytest.raises(ValueError) as exc_info:
            service.update(sample_user.id, UserUpdate(age=15))

        assert "Age must be 18" in str(exc_info.value)

# ============================================================================
# Test Lifecycle Hooks
# ============================================================================
class TestLifecycleHooks:
    """Test lifecycle hooks."""

    def test_before_create_hook(self, repository):
        """Should call before_create hook."""

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def before_create(self, data: dict) -> dict:
                # Add prefix to name
                data['name'] = f"Mr. {data['name']}"
                return data

        service = HookService(repository)

        user = service.create(UserCreate(
            name="John Doe",
            email="john@example.com"
        ))

        assert user.name == "Mr. John Doe"

    def test_after_create_hook(self, repository):
        """Should call after_create hook."""
        hook_called = []

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def after_create(self, instance: User) -> None:
                hook_called.append(instance.id)

        service = HookService(repository)

        user = service.create(UserCreate(
            name="John Doe",
            email="john@example.com"
        ))

        assert len(hook_called) == 1
        assert hook_called[0] == user.id

    def test_after_create_not_called_without_commit(self, repository):
        """Should not call after_create when commit=False."""
        hook_called = []

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def after_create(self, instance: User) -> None:
                hook_called.append(instance.id)

        service = HookService(repository)

        service.create(
            UserCreate(name="John", email="john@example.com"),
            commit=False
        )

        assert len(hook_called) == 0

    def test_before_update_hook(self, repository, sample_user):
        """Should call before_update hook."""

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def before_update(self, id, data: dict) -> dict:
                # Convert name to uppercase
                if 'name' in data:
                    data['name'] = data['name'].upper()
                return data

        service = HookService(repository)

        updated = service.update(sample_user.id, UserUpdate(name="john doe"))

        assert updated.name == "JOHN DOE"

    def test_after_update_hook(self, repository, sample_user):
        """Should call after_update hook."""
        hook_called = []

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def after_update(self, instance: User) -> None:
                hook_called.append(instance.id)

        service = HookService(repository)

        service.update(sample_user.id, UserUpdate(name="Jane"))

        assert len(hook_called) == 1
        assert hook_called[0] == sample_user.id

    def test_before_delete_hook(self, repository, sample_user):
        """Should call before_delete hook."""

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def before_delete(self, id) -> None:
                user = self.find(id)
                if user and user.status == 'active':
                    raise ValueError("Cannot delete active user")

        service = HookService(repository)

        # Should prevent deletion
        with pytest.raises(ValueError) as exc_info:
            service.delete(sample_user.id)

        assert "Cannot delete active user" in str(exc_info.value)

    def test_after_delete_hook(self, repository, sample_user):
        """Should call after_delete hook."""
        hook_called = []

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def after_delete(self, id) -> None:
                hook_called.append(id)

        service = HookService(repository)

        service.delete(sample_user.id)

        assert len(hook_called) == 1
        assert hook_called[0] == sample_user.id

    def test_hook_execution_order(self, repository):
        """Should execute hooks in correct order."""
        execution_order = []

        class HookService(BaseCrudService[User, UserCreate, UserUpdate]):
            def validate_create(self, data: UserCreate) -> None:
                execution_order.append('validate')

            def before_create(self, data: dict) -> dict:
                execution_order.append('before')
                return data

            def after_create(self, instance: User) -> None:
                execution_order.append('after')

        service = HookService(repository)

        service.create(UserCreate(name="John", email="john@example.com"))

        assert execution_order == ['validate', 'before', 'after']

# ============================================================================
# Test Integration Scenarios
# ============================================================================
class TestIntegration:
    """Test real-world integration scenarios."""

    def test_complete_user_lifecycle(self, service):
        """Should handle complete user lifecycle."""
        # Create
        user = service.create(UserCreate(
            name="John Doe",
            email="john@example.com",
            age=30
        ))
        assert user.id is not None

        # Read
        found = service.find(user.id)
        assert found.name == "John Doe"

        # Update
        updated = service.update(user.id, UserUpdate(age=31))
        assert updated.age == 31

        # Delete
        deleted = service.delete(user.id)
        assert deleted is True

        # Verify deletion
        assert service.find(user.id) is None

    def test_bulk_operations(self, service):
        """Should handle bulk operations."""
        # Bulk create
        users_data = [
            UserCreate(name=f"User {i}", email=f"user{i}@example.com", status='pending')
            for i in range(10)
        ]
        users = service.create_many(users_data)
        assert len(users) == 10

        # Bulk update
        updated_count = service.update_many(
            filters={'status': 'pending'},
            data=UserUpdate(status='active')
        )
        assert updated_count == 10

        # Verify
        active_count = service.count(status='active')
        assert active_count == 10

        # Bulk delete
        deleted_count = service.delete_many(filters={'status': 'active'})
        assert deleted_count == 10

    def test_complex_filtering_and_pagination(self, service):
        """Should handle complex queries."""
        # Create test data
        for i in range(50):
            service.create(UserCreate(
                name=f"User {i}",
                email=f"user{i}@example.com",
                age=20 + (i % 30),
                status='active' if i % 2 == 0 else 'inactive'
            ))

        # Complex filter with pagination
        users, meta = service.paginate(
            page=1,
            per_page=10,
            status='active',
            age__gte=30
        )

        assert len(users) <= 10
        assert all(u.status == 'active' for u in users)
        assert all(u.age >= 30 for u in users)
        assert meta['total'] > 0

    def test_service_with_all_hooks(self, repository):
        """Should work with all hooks together."""
        execution_log = []

        class CompleteService(BaseCrudService[User, UserCreate, UserUpdate]):
            def validate_create(self, data: UserCreate) -> None:
                execution_log.append('validate_create')
                if self.exists(email=data.email):
                    raise ValueError("Duplicate email")

            def before_create(self, data: dict) -> dict:
                execution_log.append('before_create')
                data['name'] = data['name'].upper()
                return data

            def after_create(self, instance: User) -> None:
                execution_log.append('after_create')

            def validate_update(self, id, data: UserUpdate) -> None:
                execution_log.append('validate_update')

            def before_update(self, id, data: dict) -> dict:
                execution_log.append('before_update')
                return data

            def after_update(self, instance: User) -> None:
                execution_log.append('after_update')

            def before_delete(self, id) -> None:
                execution_log.append('before_delete')

            def after_delete(self, id) -> None:
                execution_log.append('after_delete')

        service = CompleteService(repository)

        # Create
        user = service.create(UserCreate(name="john", email="john@example.com"))
        assert user.name == "JOHN"  # Modified by before_create
        assert 'validate_create' in execution_log
        assert 'before_create' in execution_log
        assert 'after_create' in execution_log

        execution_log.clear()

        # Update
        service.update(user.id, UserUpdate(age=25))
        assert 'validate_update' in execution_log
        assert 'before_update' in execution_log
        assert 'after_update' in execution_log

        execution_log.clear()

        # Delete
        service.delete(user.id)
        assert 'before_delete' in execution_log
        assert 'after_delete' in execution_log

# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_with_empty_dict(self, service):
        """Should handle empty dict gracefully."""
        with pytest.raises(Exception):  # Will fail due to missing required fields
            service.create({})

    def test_update_with_no_changes(self, service, sample_user):
        """Should handle update with no changes."""
        updated = service.update(sample_user.id, UserUpdate())

        # Should still return the instance
        assert updated is not None

    def test_pagination_empty_results(self, service):
        """Should handle pagination with no results."""
        users, meta = service.paginate(page=1, per_page=10)

        assert len(users) == 0
        assert meta['total'] == 0
        assert meta['total_pages'] == 0

    def test_pagination_beyond_last_page(self, service):
        """Should handle page beyond total pages."""
        service.create(UserCreate(name="User", email="user@example.com"))

        users, meta = service.paginate(page=100, per_page=10)

        assert len(users) == 0
        assert meta['page'] == 100

    def test_count_with_no_records(self, service):
        """Should return 0 for empty table."""
        count = service.count()

        assert count == 0

    def test_filter_with_no_matches(self, service, sample_user):
        """Should return empty list when no matches."""
        users = service.filter(name="Nonexistent")

        assert users == []