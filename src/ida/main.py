"""The main file for when the project is run."""

import os


def main() -> None:
    """Execute the main function for when the project is run."""
    ida_debug = os.environ.get("IDA_DEBUG", "1")
    print("IDA_DEBUG: ", ida_debug)
    try:
        debug = int(ida_debug)
    except ValueError:
        """Could not convert to an int, assume True."""
        debug = True

    while debug:
        """When in debug-mode, keep the program running until the user exits."""


if __name__ == "__main__":
    main()
