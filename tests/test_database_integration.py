"""
Integration tests for sync and async database operations.

Tests real-world scenarios:
- Migration from sync to async
- Mixed sync/async usage
- Connection pooling
- Read replica load balancing
- Health monitoring
- Error recovery
- Performance patterns

Target Coverage: Integration scenarios
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy import String, text, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.ext.asyncio import AsyncSession

from fastkit_core.database import (
    Base,
    IntIdMixin,
    TimestampMixin,
    DatabaseManager,
    AsyncDatabaseManager,
    init_database,
    init_async_database,
    get_db,
    get_async_db,
    shutdown_database,
    shutdown_async_database,
)
from fastkit_core.config import ConfigManager


# ============================================================================
# Test Models
# ============================================================================

class User(Base, IntIdMixin, TimestampMixin):
    """Test user model for integration tests."""
    __tablename__ = 'integration_users'

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))


class Post(Base, IntIdMixin, TimestampMixin):
    """Test post model for integration tests."""
    __tablename__ = 'integration_posts'

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[int]
