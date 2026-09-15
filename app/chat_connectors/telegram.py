import logging
from typing import Any

import httpx

from app.chat_connectors.base import BaseChatConnector
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramConnector(BaseChatConnector):
    """
    Direct asynchronous connector for Telegram Bot API using httpx.
    """

    def __init__(self, bot_token: str | None = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.bot_token.strip())

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Sends text message to Telegram chat."""
        if not self.is_configured:
            logger.info(f"[Mock Telegram] To {chat_id}: {text}")
            return True

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
                if resp.status_code != 200:
                    logger.error(f"Telegram send_message failed: {resp.status_code} {resp.text}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Telegram send_message exception: {e}")
            return False

    async def ask_for_category(self, transaction_id: str, vendor_name: str, amount: str, chat_id: str = "") -> str:
        """
        Sends an interactive prompt asking the user for a category.
        """
        prompt = (
            f"❓ *Uncategorized Transaction*\n"
            f"Vendor: `{vendor_name}`\n"
            f"Amount: `INR {amount}`\n\n"
            f"Reply with: `/cat {transaction_id} <CategoryName>`"
        )
        if chat_id:
            await self.send_message(chat_id, prompt)
        return prompt

    def start_polling(self):
        """Not required when using webhook architecture."""
        logger.info("Telegram connector using webhook-based architecture.")


telegram_connector = TelegramConnector()
