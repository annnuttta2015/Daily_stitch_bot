"""Модуль для анонимного опроса пользователей после завершения пробного периода"""
import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime
from data.storage import (
    get_user_subscription, 
    is_subscribed, 
    get_user_feedback_given, 
    set_user_feedback_given,
    get_all_user_ids
)
from config import ADMIN_IDS
from utils import safe_answer_callback

logger = logging.getLogger(__name__)

router = Router()

# Варианты ответов для опроса
FEEDBACK_OPTIONS = [
    "💰 Цена высоковата",
    "🤔 Не разобралась в функциях",
    "⏳ Не хватило времени попробовать",
    "📱 Удобнее вести в блокноте",
    "🧵 Не хватает нужных функций"
]

def get_feedback_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с вариантами ответов"""
    keyboard = []
    for option in FEEDBACK_OPTIONS:
        keyboard.append([InlineKeyboardButton(
            text=option,
            callback_data=f"feedback_{option}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def check_and_send_feedback(bot, user_id: int):
    """Проверить, нужно ли отправить опрос пользователю"""
    try:
        # Проверяем, был ли уже отправлен опрос
        if get_user_feedback_given(user_id):
            return False
        
        # Проверяем, есть ли активная подписка
        if is_subscribed(user_id):
            return False
        
        # Проверяем, была ли пробная подписка и истекла ли она
        subscription = get_user_subscription(user_id)
        if not subscription:
            return False
        
        # Проверяем, была ли это пробная подписка
        is_trial = subscription.get('isTrial', False)
        if not is_trial:
            return False
        
        # Проверяем, истекла ли подписка
        expires_at_str = subscription.get('expiresAt')
        if not expires_at_str:
            return False
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at >= datetime.now():
                # Подписка еще не истекла
                return False
        except Exception as e:
            logger.error(f"[FEEDBACK] Ошибка при парсинге даты для user_id={user_id}: {e}")
            return False
        
        # Все условия выполнены - отправляем опрос
        await send_feedback_request(bot, user_id)
        return True
        
    except Exception as e:
        logger.error(f"[FEEDBACK] Ошибка при проверке опроса для user_id={user_id}: {e}", exc_info=True)
        return False

async def send_feedback_request(bot, user_id: int):
    """Отправить запрос на опрос пользователю"""
    try:
        message_text = (
            "✨ Пробный период закончился!\n\n"
            "Если можно — поддержите улучшение Дневника ❤️\n\n"
            "Ответьте на один вопрос анонимно: что помешало оформить подписку?\n"
            "Выберите вариант ниже 👇"
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            reply_markup=get_feedback_keyboard()
        )
        logger.info(f"[FEEDBACK] Отправлен запрос на опрос для user_id={user_id}")
        
    except Exception as e:
        logger.error(f"[FEEDBACK] Ошибка при отправке запроса на опрос для user_id={user_id}: {e}", exc_info=True)

@router.callback_query(F.data.startswith("feedback_"))
async def handle_feedback_response(callback: CallbackQuery):
    """Обработчик ответа на опрос"""
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    
    try:
        # Извлекаем текст ответа из callback_data
        feedback_text = callback.data.replace("feedback_", "")
        
        # Отправляем благодарность пользователю
        await callback.message.answer(
            "Спасибо большое! 🧡\n\n"
            "Ваш ответ отправлен анонимно и помогает улучшать Дневник ✨"
        )
        
        # Отправляем анонимный ответ администраторам
        if ADMIN_IDS:
            admin_message = f"Анонимный ответ от пользователя:\n\n{feedback_text}"
            bot = callback.bot
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=admin_message
                    )
                    logger.info(f"[FEEDBACK] Ответ отправлен администратору {admin_id}")
                except Exception as e:
                    logger.error(f"[FEEDBACK] Ошибка при отправке ответа администратору {admin_id}: {e}")
        
        # Устанавливаем флаг, что опрос был пройден
        set_user_feedback_given(user_id, True)
        logger.info(f"[FEEDBACK] Пользователь user_id={user_id} прошел опрос: {feedback_text}")
        
        # Удаляем сообщение с опросом
        try:
            await callback.message.delete()
        except:
            pass
        
    except Exception as e:
        logger.error(f"[FEEDBACK] Ошибка при обработке ответа на опрос для user_id={user_id}: {e}", exc_info=True)

@router.message(Command("send_feedback"))
async def cmd_send_feedback(message: Message):
    """Команда для рассылки опроса пользователям без подписки (только для администраторов)"""
    user_id = message.from_user.id
    bot = message.bot
    
    if not ADMIN_IDS or user_id not in ADMIN_IDS:
        logger.warning(f"[FEEDBACK] Попытка использования /send_feedback от user_id={user_id} (не ADMIN)")
        return
    
    try:
        await message.answer("🔄 Начинаю рассылку опроса...")
        
        all_users = get_all_user_ids()
        logger.info(f"[FEEDBACK] Начало рассылки опроса. Всего пользователей: {len(all_users)}")
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for target_user_id in all_users:
            try:
                # Пропускаем администраторов
                if ADMIN_IDS and target_user_id in ADMIN_IDS:
                    logger.debug(f"[FEEDBACK] Пропуск user_id={target_user_id} - администратор")
                    skipped_count += 1
                    continue
                
                # Проверяем, был ли уже отправлен опрос
                if get_user_feedback_given(target_user_id):
                    logger.debug(f"[FEEDBACK] Пропуск user_id={target_user_id} - опрос уже был отправлен")
                    skipped_count += 1
                    continue
                
                # Проверяем, есть ли активная подписка
                if is_subscribed(target_user_id):
                    logger.debug(f"[FEEDBACK] Пропуск user_id={target_user_id} - есть активная подписка")
                    skipped_count += 1
                    continue
                
                # Проверяем, была ли пробная подписка (для рассылки отправляем всем без подписки)
                # Но можно добавить дополнительную проверку, если нужно отправлять только тем, у кого была пробная
                subscription = get_user_subscription(target_user_id)
                # Для рассылки отправляем всем без активной подписки, независимо от того, была ли пробная
                # Если нужно только тем, у кого была пробная, раскомментируйте следующую проверку:
                # if not subscription or not subscription.get('isTrial', False):
                #     skipped_count += 1
                #     continue
                
                # Отправляем опрос
                await send_feedback_request(bot, target_user_id)
                success_count += 1
                logger.info(f"[FEEDBACK] Опрос отправлен user_id={target_user_id}")
                
                # Небольшая задержка, чтобы избежать rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"[FEEDBACK] Ошибка при обработке user_id={target_user_id}: {e}", exc_info=True)
        
        await message.answer(
            f"✅ Рассылка завершена!\n\n"
            f"Успешно: {success_count}\n"
            f"Пропущено: {skipped_count}\n"
            f"Ошибок: {error_count}"
        )
        logger.info(f"[FEEDBACK] Рассылка завершена: success={success_count}, skipped={skipped_count}, errors={error_count}")
        
    except Exception as e:
        logger.error(f"[FEEDBACK] Критическая ошибка при рассылке: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при рассылке: {e}")

