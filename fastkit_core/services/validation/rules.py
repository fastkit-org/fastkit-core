"""Simple validation rule helpers that return Field()."""
from pydantic import Field

def min_length(length: int):
    """Minimum string length."""
    return Field(min_length=length)

def max_length(length: int):
    """Maximum string length."""
    return Field(max_length=length)

def length(min_len: int, max_len: int):
    """String length range."""
    return Field(min_length=min_len, max_length=max_len)
