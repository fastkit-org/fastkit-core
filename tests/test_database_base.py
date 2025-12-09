"""
Comprehensive tests for FastKit Core Database Base model.

Tests Base model functionality:
- Auto-generated table names
- Primary key
- Dict serialization
- Relationship handling
- Update from dict
"""

import pytest
from sqlalchemy import create_engine, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship

from fastkit_core.database import Base, IntIdMixin


# ============================================================================
# Test Models
# ============================================================================

class User(Base, IntIdMixin):
    """Test user model."""
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))


class UserProfile(Base, IntIdMixin):
    """Test model with CamelCase name."""
    bio: Mapped[str] = mapped_column(String(500))


class Category(Base, IntIdMixin):
    """Test model ending in 'y'."""
    name: Mapped[str] = mapped_column(String(100))


class Post(Base, IntIdMixin):
    """Test model with relationships."""
    title: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    # Relationship
    user: Mapped[User] = relationship(User, backref='posts')


class Comment(Base, IntIdMixin):
    """Test model with nested relationships."""
    content: Mapped[str] = mapped_column(String(500))
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'))

    post: Mapped[Post] = relationship(Post, backref='comments')

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

# ============================================================================
# Test Table Name Generation
# ============================================================================

class TestTableNames:
    """Test automatic table name generation."""

    def test_simple_name(self):
        """Should pluralize simple names."""
        assert User.__tablename__ == 'users'

    def test_camelcase_name(self):
        """Should convert CamelCase to snake_case and pluralize."""
        assert UserProfile.__tablename__ == 'user_profiles'

    def test_name_ending_in_y(self):
        """Should handle names ending in 'y'."""
        assert Category.__tablename__ == 'categories'

    def test_name_ending_in_s(self):
        """Should handle names ending in 's'."""

        class Status(Base, IntIdMixin):
            name: Mapped[str] = mapped_column(String(50))

        assert Status.__tablename__ == 'statuses'

    def test_custom_tablename(self):
        """Should allow custom table name override."""

        class CustomModel(Base, IntIdMixin):
            __tablename_override__ = 'my_custom_table'
            name: Mapped[str] = mapped_column(String(50))

        assert CustomModel.__tablename__ == 'my_custom_table'


# ============================================================================
# Test Primary Key
# ============================================================================

class TestPrimaryKey:
    """Test primary key functionality."""

    def test_has_id_column(self, session):
        """Should have auto-incrementing id."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert isinstance(user.id, int)
        assert user.id > 0

    def test_auto_increment(self, session):
        """Should auto-increment IDs."""
        user1 = User(name="John", email="john@example.com")
        user2 = User(name="Jane", email="jane@example.com")

        session.add(user1)
        session.add(user2)
        session.commit()

        assert user2.id == user1.id + 1


# ============================================================================
# Test to_dict() Serialization
# ============================================================================

class TestToDict:
    """Test to_dict() serialization."""

    def test_to_dict_basic(self, session):
        """Should convert to dict."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        data = user.to_dict()

        assert isinstance(data, dict)
        assert data['name'] == "John"
        assert data['email'] == "john@example.com"
        assert 'id' in data

    def test_to_dict_with_exclude(self, session):
        """Should exclude specified fields."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        data = user.to_dict(exclude=['email'])

        assert 'name' in data
        assert 'email' not in data
        assert 'id' in data

    def test_to_dict_datetime_serialization(self, session):
        """Should serialize datetime to ISO format."""
        from fastkit_core.database import BaseWithTimestamps

        class Article(BaseWithTimestamps, IntIdMixin):
            __tablename__='base_tmp_articles'
            title: Mapped[str] = mapped_column(String(200))

        Base.metadata.create_all(session.bind)

        article = Article(title="Test")
        session.add(article)
        session.commit()

        data = article.to_dict()

        assert isinstance(data['created_at'], str)
        assert 'T' in data['created_at']  # ISO format

    def test_to_dict_with_relationships(self, session):
        """Should include relationships when requested."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        post = Post(title="My Post", user_id=user.id)
        session.add(post)
        session.commit()

        data = post.to_dict(include_relationships=True)

        assert 'user' in data
        assert data['user']['name'] == "John"

    def test_to_dict_relationships_max_depth(self, session):
        """Should respect max_depth for nested relationships."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        post = Post(title="My Post", user_id=user.id)
        session.add(post)
        session.commit()

        comment = Comment(content="Great post!", post_id=post.id)
        session.add(comment)
        session.commit()

        # Depth 1: comment -> post (stop here)
        data = comment.to_dict(include_relationships=True, max_depth=1)
        assert 'post' in data
        assert 'user' not in data['post']  # Stopped at depth 1

        # Depth 2: comment -> post -> user
        data = comment.to_dict(include_relationships=True, max_depth=2)
        assert 'post' in data
        assert 'user' in data['post']

    def test_to_dict_with_list_relationships(self, session):
        """Should handle one-to-many relationships."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        post1 = Post(title="Post 1", user_id=user.id)
        post2 = Post(title="Post 2", user_id=user.id)
        session.add_all([post1, post2])
        session.commit()

        data = user.to_dict(include_relationships=True)

        assert 'posts' in data
        assert isinstance(data['posts'], list)
        assert len(data['posts']) == 2

    def test_to_json_alias(self, session):
        """Should work as alias for to_dict()."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        data = user.to_json()

        assert isinstance(data, dict)
        assert data['name'] == "John"


# ============================================================================
# Test update_from_dict()
# ============================================================================

class TestUpdateFromDict:
    """Test update_from_dict() method."""

    def test_update_from_dict_basic(self, session):
        """Should update attributes from dict."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        user.update_from_dict({
            'name': 'Jane',
            'email': 'jane@example.com'
        })
        session.commit()

        assert user.name == 'Jane'
        assert user.email == 'jane@example.com'

    def test_update_from_dict_partial(self, session):
        """Should update only specified fields."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        user.update_from_dict({'name': 'Jane'})
        session.commit()

        assert user.name == 'Jane'
        assert user.email == 'john@example.com'  # Unchanged

    def test_update_from_dict_with_exclude(self, session):
        """Should exclude specified fields."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        user.update_from_dict(
            {'name': 'Jane', 'email': 'jane@example.com'},
            exclude=['email']
        )

        assert user.name == 'Jane'
        assert user.email == 'john@example.com'  # Excluded

    def test_update_from_dict_with_allow_only(self, session):
        """Should only update allowed fields."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        user.update_from_dict(
            {'name': 'Jane', 'email': 'jane@example.com'},
            allow_only=['name']
        )

        assert user.name == 'Jane'
        assert user.email == 'john@example.com'  # Not in allow_only

    def test_update_from_dict_ignores_nonexistent(self, session):
        """Should ignore non-existent attributes."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        user.update_from_dict({
            'name': 'Jane',
            'nonexistent_field': 'value'
        })

        assert user.name == 'Jane'
        assert not hasattr(user, 'nonexistent_field')

    def test_update_from_dict_ignores_id(self, session):
        """Should not update ID."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        original_id = user.id

        user.update_from_dict({
            'id': 999,
            'name': 'Jane'
        })

        assert user.id == original_id  # ID unchanged
        assert user.name == 'Jane'

# ============================================================================
# Test __repr__()
# ============================================================================

class TestRepr:
    """Test string representation."""

    def test_repr_default(self, session):
        """Should have default repr with ID."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        repr_str = repr(user)

        assert 'User' in repr_str
        assert str(user.id) in repr_str

    def test_repr_custom(self, session):
        """Should allow custom repr attributes."""

        class CustomUser(Base, IntIdMixin):
            name: Mapped[str] = mapped_column(String(100))

            def __repr_attrs__(self):
                return [('id', self.id), ('name', self.name)]

        Base.metadata.create_all(session.bind)

        user = CustomUser(name="John")
        session.add(user)
        session.commit()

        repr_str = repr(user)

        assert 'CustomUser' in repr_str
        assert 'name=' in repr_str
        assert 'John' in repr_str


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases."""

    def test_to_dict_with_none_values(self, session):
        """Should handle None values."""

        class OptionalModel(Base, IntIdMixin):
            name: Mapped[str] = mapped_column(String(100))
            optional: Mapped[str | None] = mapped_column(String(100), nullable=True)

        Base.metadata.create_all(session.bind)

        model = OptionalModel(name="Test", optional=None)
        session.add(model)
        session.commit()

        data = model.to_dict()

        assert data['optional'] is None

    def test_to_dict_empty_relationships(self, session):
        """Should handle empty relationships."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        data = user.to_dict(include_relationships=True)

        assert 'posts' in data
        assert data['posts'] == []

    def test_update_from_dict_empty_dict(self, session):
        """Should handle empty dict."""
        user = User(name="John", email="john@example.com")
        session.add(user)
        session.commit()

        original_name = user.name

        user.update_from_dict({})

        assert user.name == original_name