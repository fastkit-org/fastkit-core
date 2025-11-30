from fastapi import Query
from typing import Annotated

def get_pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20
) -> dict:
    """Pagination parameters."""
    return {
        'page': page,
        'per_page': per_page,
        'offset': (page - 1) * per_page
    }