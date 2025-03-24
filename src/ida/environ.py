"""Module for working with environment variables."""

import os
from collections.abc import Callable
from typing import TypeVar

try:
    from dotenv import load_dotenv
except ImportError:
    """Could not import dotenv.load_dotenv."""
else:
    load_dotenv()

T = TypeVar("T")


class MissingEnvironmentVariableError(Exception):
    """Raised when an environment variable is missing."""


class _Missing:
    """Sentinel to represent a missing value."""


_MISSING = _Missing()


def from_env(name: str, default: T | _Missing = _MISSING, astype: Callable[..., T] = str) -> T:
    """Get a value from the environment and call astype with the value as argument.

    If the default is returned, it will be returned as provided.
    A MissingEnvironmentVariableError will be raised if the environment variable is not set and no default is provided.
    """
    try:
        value = os.environ[name]
    except KeyError as exc:
        if isinstance(default, _Missing):
            raise MissingEnvironmentVariableError(f"Environment variable {name} is not set.") from exc
        return default
    return astype(value)


def strtobool(value: str) -> bool:
    """Convert a string to a boolean.

    The provided value is converted to lowercase before comparing.

    The following values are considered True:
        - "true"
        - "1"
        - "t"
        - "y"
        - "yes"

    All other values are considered False.
    """
    return value.lower() in ("true", "1", "t", "y", "yes")
