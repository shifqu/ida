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


def from_env(name: str, default: str | None = None, astype: Callable[..., T] = str) -> T:
    """Get a value from the environment and call astype with the value as argument.

    The default will also be passed to astype if it is not None.
    A ValueError will be raised if the environment variable is not set and no default is provided.
    """
    try:
        value = os.environ[name]
    except KeyError as exc:
        if default is None:
            raise MissingEnvironmentVariableError(f"Environment variable {name} is not set.") from exc
        return astype(default)
    return astype(value)


def strtobool(value: str) -> bool:
    """Convert a string to a boolean.

    The following values are considered True:
        - "true"
        - "1"
        - "t"
        - "y"
        - "yes"
    """
    return value.lower() in ("true", "1", "t", "y", "yes")
