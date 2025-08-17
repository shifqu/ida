"""Telegram types."""

from typing import cast


class TelegramUpdate:
    """Represent a normalized Telegram update."""

    def __init__(self, update: dict):
        """Initialize the normalized Telegram update."""
        self.message = cast(dict | None, update.get("message"))
        self.callback_query = cast(dict | None, update.get("callback_query"))

        if self.message and "text" in self.message:
            self.chat_id = int(self.message["chat"]["id"])
            self.message_id = 0
            self.message_text = str(self.message["text"])
            self.callback_data = ""
        elif self.callback_query:
            self.chat_id = int(self.callback_query["message"]["chat"]["id"])
            self.message_id = int(self.callback_query["message"]["message_id"])
            self.message_text = ""
            self.callback_data = str(self.callback_query.get("data"))
        else:
            raise ValueError("Unsupported Telegram update format")

    def is_message(self):
        """Return the message part of the update."""
        return self.message is not None

    def is_callback_query(self):
        """Return the callback query part of the update."""
        return self.callback_query is not None

    def is_command(self):
        """Check if the update is a command."""
        return self.is_message() and self.message_text.startswith("/")
