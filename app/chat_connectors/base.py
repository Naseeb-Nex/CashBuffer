import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseChatConnector(ABC):
    """
    Abstract base class for messaging app connectors (Telegram, WhatsApp, etc.).
    Keeps the business logic decoupled from the delivery mechanism.
    """

    @abstractmethod
    async def send_message(self, chat_id: str, text: str):
        """Sends a text message to the specified chat."""

    @abstractmethod
    async def ask_for_category(
        self, transaction_id: str, vendor_name: str, amount: str
    ) -> str:
        """
        Sends an interactive prompt asking the user for a category.
        Returns the category name chosen by the user.
        """

    @abstractmethod
    def start_polling(self):
        """Start listening for incoming messages (e.g. for a long-running daemon)."""
