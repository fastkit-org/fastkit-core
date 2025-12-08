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