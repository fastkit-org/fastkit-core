"""Simple validation rule helpers that return Field()."""
from pydantic import Field

def min_length(length: int):
    """Minimum string length."""
    return Field(min_length=length)

def max_length(length: int):
    """Maximum string length."""
    return Field(max_length=length)