"""Utility functions for the IDA project."""

from pathlib import Path


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


def existing_path(value: str | Path) -> Path:
    """Convert the value to a Path and ensure it exists.

    Prints a warning if the file could not be created.
    """
    path = Path(value)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    except Exception as e:
        print(f"[WARNING] Could not create log file {path}: {e}")
    return path


def existing_str_path(value: str | Path) -> str:
    """Convert the path to a string."""
    path = existing_path(value)
    return str(path)
