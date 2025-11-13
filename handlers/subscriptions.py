from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime, timedelta
from data.storage import save_subscription, is_subscribed, get_user_subscription
from config import SUBSCRIPTION_ID, TEST_MODE
from handlers.keyboards import get_main_menu
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "subscribe")
async def callback_subscribe(callback: CallbackQuery):
    """Показать информацию о подписке"""
    await callback.answer()
    
    if TEST_MODE:
        await callback.message.answer(
            'ℹ️ <b>Тестовый режим</b>\n\n'
            'В данный момент бот работает в тестовом режиме.\n'
            'Подписка не требуется. Все функции доступны.',
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
        return
    
    if not SUBSCRIPTION_ID:
        await callback.message.answer(
            '⚠️ <b>Подписка временно недоступна</b>\n\n'
            'Подписка будет настроена в ближайшее время.\n'
            'Попробуйте позже.',
            parse_mode='HTML'
        )
        return
    
    # Проверяем, есть ли уже активная подписка
    subscription = get_user_subscription(callback.from_user.id)
    if subscription and is_subscribed(callback.from_user.id):
        expires_at = subscription.get('expiresAt')
        if expires_at:
            try:
                expire_date = datetime.fromisoformat(expires_at)
                await callback.message.answer(
                    f'✅ <b>У вас уже есть активная подписка!</b>\n\n'
                    f'Подписка действительна до: {expire_date.strftime("%d.%m.%Y")}',
                    parse_mode='HTML',
                    reply_markup=get_main_menu()
                )
                return
            except:
                pass
    
    # Здесь будет отправка инвойса для подписки
    # Пока просто сообщение, что подписка будет настроена
    await callback.message.answer(
        '💳 <b>Оформление подписки</b>\n\n'
        'Подписка будет настроена после подключения платежей через BotFather.\n\n'
        'Стоимость: 99₽/месяц\n'
        'Доступ ко всем функциям бота.',
        parse_mode='HTML'
    )

# Обработчик успешной подписки
@router.message(lambda msg: msg.successful_payment is not None)
async def process_subscription_payment(message: Message):
    """Обработка успешной оплаты подписки"""
    user_id = message.from_user.id
    payment = message.successful_payment
    
    # Сохраняем информацию о подписке
    expires_at = datetime.now() + timedelta(days=30)  # 1 месяц
    subscription_data = {
        'active': True,
        'expiresAt': expires_at.isoformat(),
        'subscriptionId': SUBSCRIPTION_ID,
        'paymentDate': datetime.now().isoformat(),
        'invoicePayload': payment.invoice_payload
    }
    
    save_subscription(user_id, subscription_data)
    
    await message.answer(
        '✅ <b>Подписка активирована!</b>\n\n'
        f'Подписка действительна до: {expires_at.strftime("%d.%m.%Y")}\n\n'
        'Теперь вы можете использовать все функции бота.',
        parse_mode='HTML',
        reply_markup=get_main_menu()
    )

# Обработчик pre-checkout запроса (подтверждение оплаты)
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработка запроса на подтверждение оплаты"""
    await pre_checkout_query.answer(ok=True)

# Обработчик проверки статуса подписки
@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    """Проверить статус подписки"""
    await callback.answer()
    user_id = callback.from_user.id
    
    if TEST_MODE:
        await callback.message.answer(
            'ℹ️ <b>Тестовый режим</b>\n\n'
            'В данный момент бот работает в тестовом режиме.\n'
            'Подписка не требуется.',
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
        return
    
    subscription = get_user_subscription(user_id)
    if subscription and is_subscribed(user_id):
        expires_at = subscription.get('expiresAt')
        if expires_at:
            try:
                expire_date = datetime.fromisoformat(expires_at)
                await callback.message.answer(
                    f'✅ <b>Активная подписка</b>\n\n'
                    f'Подписка действительна до: {expire_date.strftime("%d.%m.%Y")}\n'
                    f'Осталось дней: {(expire_date - datetime.now()).days}',
                    parse_mode='HTML',
                    reply_markup=get_main_menu()
                )
                return
            except:
                pass
        
        await callback.message.answer(
            '✅ <b>Активная подписка</b>\n\n'
            'У вас есть активная подписка.',
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
    else:
        await callback.message.answer(
            '❌ <b>Подписка отсутствует</b>\n\n'
            'У вас нет активной подписки.\n'
            'Оформите подписку для доступа к боту.',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text='💳 Оформить подписку',
                    callback_data='subscribe'
                )
            ]])
        )

