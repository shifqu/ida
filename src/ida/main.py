"""The main file for when the project is run."""

import os


def main() -> None:
    """Execute the main function for when the project is run."""
    print("Hello, world!")
    default_value = "IDA_DEBUG environment variable not found."
    print(os.environ.get("IDA_DEBUG", default_value))


if __name__ == "__main__":
    main()
