from fastkit_core.database.mixins import TimestampMixin
from fastkit_core.database.base import Base


class BaseWithTimestamps(Base, TimestampMixin):
    """
    Convenience base class with timestamps included.

    Use this for most models that need timestamps.
    If you don't need timestamps, use Base directly.

    Example:
        # Most common case - with timestamps
        class User(BaseWithTimestamps):
            name: Mapped[str]

        # Without timestamps
        class LogEntry(Base):
            message: Mapped[str]
    """
    __abstract__ = True