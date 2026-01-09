"""
Comprehensive tests for SlugServiceMixin.

Tests both async and sync slug generation with:
- Basic slug generation
- Uniqueness checking
- Auto-increment for duplicates
- Unicode handling
- Custom parameters
- Edge cases
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fastkit_core.services import AsyncBaseCrudService, BaseCrudService, SlugServiceMixin
from fastkit_core.database import AsyncRepository, Repository


# ============================================================================
# Test Models & Schemas
# ============================================================================

class Base(DeclarativeBase):
    """Base for test models."""
    pass


class Article(Base):
    """Test article model with slug."""
    __tablename__ = 'test_articles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
