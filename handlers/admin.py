"""Административные команды для управления подписками"""
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime
from data.storage import grant_access, get_all_user_ids, get_user_subscription, is_subscribed
from config import ADMIN_IDS
from handlers.subscription_notifications import reset_notification_flags
import logging
import asyncio

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

@router.message(Command("send_trial"))
async def cmd_send_trial(message: Message):
    """Рассылка пробной подписки на 3 дня всем пользователям без активной подписки"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Команда недоступна")
        logger.warning(f"[ADMIN] Попытка использования /send_trial от user_id={user_id} (не ADMIN)")
        return
    
    try:
        bot = message.bot
        all_users = get_all_user_ids()
        
        if not all_users:
            await message.answer("❌ Нет пользователей для рассылки")
            return
        
        await message.answer(f"🔄 Начинаю рассылку пробных подписок...\nВсего пользователей: {len(all_users)}")
        
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for target_user_id in all_users:
            try:
                # Проверяем, есть ли активная подписка
                if is_subscribed(target_user_id):
                    skipped_count += 1
                    logger.debug(f"[ADMIN] Пропуск user_id={target_user_id} - есть активная подписка")
                    continue
                
                # Проверяем, была ли уже выдана пробная подписка
                subscription = get_user_subscription(target_user_id)
                if subscription and subscription.get('isTrial'):
                    skipped_count += 1
                    logger.debug(f"[ADMIN] Пропуск user_id={target_user_id} - уже получал пробную подписку")
                    continue
                
                # Выдаем пробную подписку на 3 дня
                expires_at = grant_access(target_user_id, days=3, is_trial=True)
                logger.info(f"[ADMIN] Выдана пробная подписка user_id={target_user_id}, expires_at={expires_at}")
                
                # Отправляем сообщение пользователю
                try:
                    await bot.send_message(
                        chat_id=target_user_id,
                        text=(
                            '🎁 <b>Специальное предложение!</b>\n\n'
                            'Мы предоставляем вам <b>пробную подписку на 3 дня</b>!\n\n'
                            f'Подписка действует до: {expires_at.strftime("%d.%m.%Y")}\n\n'
                            'Попробуйте все функции бота:\n'
                            '• Добавление крестиков\n'
                            '• Статистика и прогресс\n'
                            '• Проекты с фото\n'
                            '• Челленджи и планы\n'
                            '• И многое другое!\n\n'
                            'После окончания пробного периода для продолжения использования потребуется оформление подписки (99₽/мес).\n\n'
                            'Нажмите /start для начала работы!'
                        ),
                        parse_mode='HTML'
                    )
                    success_count += 1
                    logger.info(f"[ADMIN] Сообщение отправлено user_id={target_user_id}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"[ADMIN] Ошибка при отправке сообщения user_id={target_user_id}: {e}")
                
                # Небольшая задержка, чтобы не перегружать API Telegram
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"[ADMIN] Ошибка при обработке user_id={target_user_id}: {e}", exc_info=True)
        
        # Отправляем отчет администратору
        report = (
            f'✅ <b>Рассылка завершена</b>\n\n'
            f'📊 Статистика:\n'
            f'✅ Отправлено успешно: {success_count}\n'
            f'⏭️ Пропущено: {skipped_count}\n'
            f'❌ Ошибок: {error_count}\n'
            f'📊 Всего пользователей: {len(all_users)}'
        )
        
        await message.answer(report, parse_mode='HTML')
        logger.info(f"[ADMIN] Рассылка завершена: success={success_count}, skipped={skipped_count}, errors={error_count}")
        
    except Exception as e:
        logger.error(f"[ADMIN] Критическая ошибка при рассылке: {e}", exc_info=True)
        await message.answer(f"❌ Критическая ошибка при рассылке: {e}")

