"""Утилиты для бота"""
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)


async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """
    Безопасно отвечает на callback query, игнорируя ошибки устаревших запросов
    
    Args:
        callback: CallbackQuery объект
        text: Текст ответа (опционально)
        show_alert: Показать ли alert вместо toast (по умолчанию False)
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as e:
        # Игнорируем ошибки "query is too old" - это нормально для устаревших callback queries
        if "query is too old" in str(e) or "query ID is invalid" in str(e):
            logger.debug(f"Ignoring expired callback query: {callback.data}")
        else:
            # Для других ошибок логируем
            logger.warning(f"Error answering callback query: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error answering callback query: {e}", exc_info=True)
        # Не пробрасываем исключение, чтобы не ломать обработку

