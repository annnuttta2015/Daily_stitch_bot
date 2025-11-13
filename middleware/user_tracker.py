"""Middleware для отслеживания пользователей"""
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from data.storage import save_user_id

class UserTrackerMiddleware(BaseMiddleware):
    """Middleware для автоматического сохранения ID пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        user = None
        
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user
        elif hasattr(event, 'from_user') and event.from_user:
            user = event.from_user
        
        # Сохраняем ID пользователя
        if user:
            save_user_id(user.id)
        
        # Продолжаем обработку
        return await handler(event, data)

