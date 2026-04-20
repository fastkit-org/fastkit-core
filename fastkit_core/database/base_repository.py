from sqlalchemy.orm import Load
from sqlalchemy import func, select
from typing import Sequence, Any
import base64
import json
from datetime import datetime


class _BaseRepositoryMixin:
    model: Any

    LOOKUP_OPERATORS = {
        'eq': lambda col, val: col == val,
        'ne': lambda col, val: col != val,
        'lt': lambda col, val: col < val,
        'lte': lambda col, val: col <= val,
        'gt': lambda col, val: col > val,
        'gte': lambda col, val: col >= val,
        'in': lambda col, val: col.in_(val),
        'not_in': lambda col, val: col.not_in(val),
        'like': lambda col, val: col.like(val),
        'ilike': lambda col, val: col.ilike(val),
        'is_null': lambda col, val: col.is_(None) if val else col.isnot(None),
        'is_not_null': lambda col, val: col.isnot(None),
        'between': lambda col, val: col.between(val[0], val[1]),
        'startswith': lambda col, val: col.like(f'{val}%'),
        'endswith': lambda col, val: col.like(f'%{val}'),
        'contains': lambda col, val: col.like(f'%{val}%'),
    }

    def _apply_ordering(self, query, order_by: str | list[str] | None):
        if not order_by:
            return query

        fields = [order_by] if isinstance(order_by, str) else order_by

        for field in fields:
            if field.startswith('-'):
                col = field[1:]
                if hasattr(self.model, col):
                    query = query.order_by(getattr(self.model, col).desc())
            else:
                if hasattr(self.model, field):
                    query = query.order_by(getattr(self.model, field))

        return query

    def _apply_eager_loading(
            self,
            stmt,
            load: Sequence[Load] | None = None
    ):
        """
        Apply eager loading options to statement.

        Uses SQLAlchemy's native Load objects for type-safe relationship loading.

        Args:
            stmt: SQLAlchemy select statement
            load: Sequence of SQLAlchemy Load objects (selectinload, joinedload, etc.)

        Returns:
            Statement with eager loading options applied

        Example:
            from sqlalchemy.orm import selectinload

            # Single relationship
            stmt = self._apply_eager_loading(
                stmt,
                [selectinload(Invoice.items)]
            )

            # Nested relationships
            stmt = self._apply_eager_loading(
                stmt,
                [selectinload(Invoice.items).selectinload(InvoiceItem.product)]
            )

            # Multiple relationships
            stmt = self._apply_eager_loading(
                stmt,
                [
                    selectinload(Invoice.client),
                    selectinload(Invoice.items).selectinload(InvoiceItem.product)
                ]
            )
        """
        if not load:
            return stmt

        # Simply apply each SQLAlchemy Load object to the statement
        for load_option in load:
            stmt = stmt.options(load_option)

        return stmt

    def _encode_cursor(self, value: Any) -> str:
        if isinstance(value, datetime):
            value = value.isoformat()
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode()

    def _decode_cursor(self, cursor: str) -> Any:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())

    def _has_soft_delete(self) -> bool:
        """Check if model has soft delete support."""
        return hasattr(self.model, 'deleted_at')

    def query(self):
        """Get query builder for complex queries."""
        return select(self.model)
