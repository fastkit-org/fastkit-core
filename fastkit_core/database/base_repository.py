
class _BaseRepositoryMixin:

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