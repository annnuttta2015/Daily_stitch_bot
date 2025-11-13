"""Административные команды для управления подписками"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime
from data.storage import grant_access
from config import ADMIN_IDS
from handlers.subscription_notifications import reset_notification_flags
import logging

router = Router()
logger = logging.getLogger(__name__)

# ID администратора (создателя бота) - берем первый из списка ADMIN_IDS
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else None

def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return user_id in ADMIN_IDS if ADMIN_IDS else False

@router.message(Command("grant_me"))
async def cmd_grant_me(message: Message):
    """Выдать бесплатный доступ создателю бота"""
    user_id = message.from_user.id
    
    if not ADMIN_ID or user_id != ADMIN_ID:
        await message.answer("⛔ Команда недоступна")
        logger.warning(f"[ADMIN] Попытка использования /grant_me от user_id={user_id} (не ADMIN)")
        return
    
    try:
        expires_at = grant_access(user_id, days=36500)  # ~100 лет
        reset_notification_flags(user_id)  # Сбрасываем флаги уведомлений
        await message.answer("💛 Бесплатный доступ активирован!")
        logger.info(f"[ADMIN] Доступ выдан создателю (user_id={user_id}) до {expires_at.strftime('%d.%m.%Y')}")
    except Exception as e:
        logger.error(f"[ADMIN] Ошибка при выдаче доступа создателю: {e}", exc_info=True)
        await message.answer("❌ Ошибка при выдаче доступа")

@router.message(Command("grant"))
async def cmd_grant(message: Message):
    """Выдать доступ пользователю на указанное количество дней"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Команда недоступна")
        logger.warning(f"[ADMIN] Попытка использования /grant от user_id={user_id} (не ADMIN)")
        return
    
    try:
        # Разбираем аргументы: /grant <user_id> <days>
        args = message.text.split()[1:] if message.text else []
        
        if len(args) < 2:
            await message.answer("❌ Использование: /grant <user_id> <days>")
            return
        
        target_user_id = int(args[0])
        days = int(args[1])
        
        if days <= 0:
            await message.answer("❌ Количество дней должно быть положительным")
            return
        
        expires_at = grant_access(target_user_id, days=days)
        reset_notification_flags(target_user_id)  # Сбрасываем флаги уведомлений
        date_str = expires_at.strftime("%d.%m.%Y")
        await message.answer(f"🎁 Доступ пользователю {target_user_id} выдан до {date_str}")
        logger.info(f"[ADMIN] Доступ выдан user_id={target_user_id} на {days} дней до {date_str}")
        
    except ValueError as e:
        await message.answer("❌ Неверный формат аргументов. Использование: /grant <user_id> <days>")
        logger.warning(f"[ADMIN] Ошибка парсинга аргументов: {e}")
    except Exception as e:
        logger.error(f"[ADMIN] Ошибка при выдаче доступа: {e}", exc_info=True)
        await message.answer("❌ Ошибка при выдаче доступа")

