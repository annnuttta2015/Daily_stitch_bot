"""Модуль для уведомлений об истечении подписки"""
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.storage import get_user_subscription, get_all_user_ids

logger = logging.getLogger(__name__)

# Хранилище для отслеживания отправленных уведомлений
# Формат: {user_id: {'3days': bool, 'expired': bool}}
sent_notifications = {}

async def check_expiring_subscriptions(bot: Bot):
    """Проверка подписок, которые скоро истекают или истекли"""
    try:
        logger.info("[SUBSCRIPTION_NOTIFICATIONS] Начало проверки подписок")
        
        # Получаем всех пользователей
        user_ids = get_all_user_ids()
        logger.debug(f"[SUBSCRIPTION_NOTIFICATIONS] Проверка {len(user_ids)} пользователей")
        
        today = datetime.now().date()
        three_days_later = today + timedelta(days=3)
        
        for user_id in user_ids:
            try:
                subscription = get_user_subscription(user_id)
                if not subscription:
                    continue
                
                expires_at_str = subscription.get('expiresAt')
                if not expires_at_str:
                    continue
                
                try:
                    expires_at = datetime.fromisoformat(expires_at_str).date()
                except:
                    logger.warning(f"[SUBSCRIPTION_NOTIFICATIONS] Не удалось распарсить дату для user_id={user_id}: {expires_at_str}")
                    continue
                
                # Инициализируем запись для пользователя, если её нет
                if user_id not in sent_notifications:
                    sent_notifications[user_id] = {'3days': False, 'expired': False}
                
                # Проверяем, истекла ли подписка
                if expires_at < today:
                    # Подписка истекла
                    if not sent_notifications[user_id]['expired']:
                        await send_expired_notification(bot, user_id, expires_at)
                        sent_notifications[user_id]['expired'] = True
                        logger.info(f"[SUBSCRIPTION_NOTIFICATIONS] Отправлено уведомление об истечении для user_id={user_id}")
                
                # Проверяем, истекает ли подписка через 3 дня или меньше (но еще не истекла)
                elif today <= expires_at <= three_days_later:
                    if not sent_notifications[user_id]['3days']:
                        await send_3days_notification(bot, user_id, expires_at)
                        sent_notifications[user_id]['3days'] = True
                        logger.info(f"[SUBSCRIPTION_NOTIFICATIONS] Отправлено уведомление за 3 дня для user_id={user_id}")
                
                # Сбрасываем флаги, если подписка была продлена (больше чем на 3 дня)
                if expires_at > three_days_later:
                    sent_notifications[user_id] = {'3days': False, 'expired': False}
                    
            except Exception as e:
                logger.error(f"[SUBSCRIPTION_NOTIFICATIONS] Ошибка при проверке подписки user_id={user_id}: {e}", exc_info=True)
                continue
        
        logger.info("[SUBSCRIPTION_NOTIFICATIONS] Проверка подписок завершена")
        
    except Exception as e:
        logger.error(f"[SUBSCRIPTION_NOTIFICATIONS] Критическая ошибка при проверке подписок: {e}", exc_info=True)

async def send_3days_notification(bot: Bot, user_id: int, expires_at: datetime.date):
    """Отправить уведомление за 3 дня до истечения подписки"""
    try:
        expires_str = expires_at.strftime("%d.%m.%Y")
        days_left = (expires_at - datetime.now().date()).days
        
        # Формируем правильное склонение для слова "день"
        if days_left == 1:
            days_text = "1 день"
        elif days_left in [2, 3, 4]:
            days_text = f"{days_left} дня"
        else:
            days_text = f"{days_left} дней"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text='💳 Продлить подписку',
                callback_data='subscribe'
            )
        ]])
        
        message_text = (
            '⏰ <b>Напоминание о подписке</b>\n\n'
            f'Ваша подписка истекает через {days_text}.\n'
            f'Дата окончания: {expires_str}\n\n'
            'Чтобы продолжить пользоваться ботом, продлите подписку.'
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"[SUBSCRIPTION_NOTIFICATIONS] Ошибка при отправке уведомления за 3 дня для user_id={user_id}: {e}", exc_info=True)

async def send_expired_notification(bot: Bot, user_id: int, expires_at: datetime.date):
    """Отправить уведомление об истечении подписки"""
    try:
        expires_str = expires_at.strftime("%d.%m.%Y")
        
        # Проверяем, была ли это пробная подписка
        subscription = get_user_subscription(user_id)
        is_trial = subscription and subscription.get('isTrial', False)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text='💳 Оформить подписку',
                callback_data='subscribe'
            )
        ]])
        
        if is_trial:
            message_text = (
                '⏰ <b>Пробная подписка закончилась</b>\n\n'
                f'Ваша пробная подписка на 3 дня завершилась {expires_str}.\n\n'
                'Надеемся, вам понравилось пользоваться ботом! 🎉\n\n'
                'Для продолжения работы с ботом необходимо оформить подписку (99₽/мес).\n'
                'Все ваши данные сохранены и будут доступны после оформления подписки.'
            )
        else:
            message_text = (
                '❌ <b>Подписка истекла</b>\n\n'
                f'Ваша подписка закончилась {expires_str}.\n\n'
                'Для продолжения работы с ботом необходимо продлить подписку.\n'
                'Все ваши данные сохранены и будут доступны после продления.'
            )
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"[SUBSCRIPTION_NOTIFICATIONS] Ошибка при отправке уведомления об истечении для user_id={user_id}: {e}", exc_info=True)

async def subscription_checker_task(bot: Bot):
    """Фоновая задача для периодической проверки подписок"""
    logger.info("[SUBSCRIPTION_NOTIFICATIONS] Запуск фоновой задачи проверки подписок")
    
    while True:
        try:
            await check_expiring_subscriptions(bot)
            # Проверяем раз в день (86400 секунд = 24 часа)
            await asyncio.sleep(86400)
        except asyncio.CancelledError:
            logger.info("[SUBSCRIPTION_NOTIFICATIONS] Задача проверки подписок остановлена")
            break
        except Exception as e:
            logger.error(f"[SUBSCRIPTION_NOTIFICATIONS] Ошибка в фоновой задаче: {e}", exc_info=True)
            # При ошибке ждем час перед следующей попыткой
            await asyncio.sleep(3600)

def reset_notification_flags(user_id: int):
    """Сбросить флаги уведомлений для пользователя (вызывается при продлении подписки)"""
    if user_id in sent_notifications:
        sent_notifications[user_id] = {'3days': False, 'expired': False}
        logger.debug(f"[SUBSCRIPTION_NOTIFICATIONS] Сброшены флаги уведомлений для user_id={user_id}")

