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

def min_value(value: int | float):
    """Minimum numeric value."""
    return Field(ge=value)

def max_value(value: int | float):
    """Maximum numeric value."""
    return Field(le=value)

def between(min_val: int | float, max_val: int | float):
    """Numeric range."""
    return Field(ge=min_val, le=max_val)

def pattern(regex: str):
    """Regex pattern validation."""
    return Field(pattern=regex)
