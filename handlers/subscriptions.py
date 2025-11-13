from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command
from datetime import datetime, timedelta
from data.storage import save_subscription, is_subscribed, get_user_subscription
from config import SUBSCRIPTION_ID, TEST_MODE, PROVIDER_TOKEN
from handlers.keyboards import get_main_menu
from utils import safe_answer_callback
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "subscribe")
async def callback_subscribe(callback: CallbackQuery):
    """Показать информацию о подписке"""
    await safe_answer_callback(callback)
    
    if TEST_MODE:
        await callback.message.answer(
            'ℹ️ <b>Тестовый режим</b>\n\n'
            'В данный момент бот работает в тестовом режиме.\n'
            'Подписка не требуется. Все функции доступны.',
            parse_mode='HTML',
            reply_markup=get_main_menu()
        )
        return
    
    # SUBSCRIPTION_ID не обязателен для работы подписок
    # Можно оставить пустым, инвойс будет отправляться без него
    
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
    
    # Отправка инвойса для подписки
    try:
        # Используем бот из контекста
        bot = callback.bot
        
        # Для работы платежей нужно получить provider_token от BotFather
        # После подключения ЮKassa в BotFather (/mybots → Payments → Connect YooKassa)
        # BotFather выдаст provider_token, который нужно добавить в .env как PROVIDER_TOKEN
        
        # Пробуем отправить инвойс
        # Если PROVIDER_TOKEN не указан, но провайдер подключен через BotFather,
        # можно попробовать использовать пустую строку (не всегда работает)
        provider_token_to_use = PROVIDER_TOKEN if PROVIDER_TOKEN else ""
        
        if not PROVIDER_TOKEN:
            # Пробуем отправить без токена (если провайдер подключен через BotFather)
            # Если не сработает, покажем инструкцию
            try:
                await bot.send_invoice(
                    chat_id=callback.from_user.id,
                    title="Подписка на дневник вышивальщицы",
                    description="Ежемесячная подписка на доступ к боту. Включает все функции: учет крестиков, статистику, календарь, работы с фото, планы, челленджи и многое другое.",
                    payload=f"subscription_{callback.from_user.id}_{int(datetime.now().timestamp())}",
                    provider_token="",  # Пробуем без токена
                    currency="RUB",
                    prices=[LabeledPrice(label="Подписка на 1 месяц", amount=9900)],
                    start_parameter="subscription"
                )
                return  # Если получилось, выходим
            except:
                # Если не получилось, показываем инструкцию
                await callback.message.answer(
                    '⚠️ <b>Платежи не настроены</b>\n\n'
                    'Для работы подписок необходимо:\n\n'
                    '<b>1. Подключить ЮKassa в BotFather:</b>\n'
                    '• Откройте @BotFather → /mybots → выберите бота\n'
                    '• Payments → Connect ЮKassa Test (для теста) или Live\n'
                    '• Следуйте инструкциям бота ЮKassa\n\n'
                    '<b>2. Получить provider_token:</b>\n'
                    'После подключения BotFather должен отправить вам сообщение с provider_token.\n'
                    'Если токен не пришел:\n'
                    '• Проверьте, что подключение завершено\n'
                    '• Попробуйте отправить /mybots → Payments снова\n'
                    '• Токен может быть в формате: <code>XXXX:XXXX:XXXX</code>\n\n'
                    '<b>3. Добавить токен в .env:</b>\n'
                    'PROVIDER_TOKEN=ваш_токен_от_BotFather',
                    parse_mode='HTML'
                )
                return
        
        # Отправляем инвойс для подписки с токеном
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Подписка на дневник вышивальщицы",
            description="Ежемесячная подписка на доступ к боту. Включает все функции: учет крестиков, статистику, календарь, работы с фото, планы, челленджи и многое другое.",
            payload=f"subscription_{callback.from_user.id}_{int(datetime.now().timestamp())}",
            provider_token=PROVIDER_TOKEN,
            currency="RUB",
            prices=[LabeledPrice(label="Подписка на 1 месяц", amount=9900)],  # 99₽ = 9900 копеек
            start_parameter="subscription"  # Параметр для идентификации подписки
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при отправке инвойса: {e}", exc_info=True)
        
        # Более понятное сообщение об ошибке
        if "PAYMENT_PROVIDER_INVALID" in error_msg or "provider_token" in error_msg.lower():
            await callback.message.answer(
                '⚠️ <b>Платежный провайдер не настроен</b>\n\n'
                'Для работы подписок необходимо подключить ЮKassa в BotFather.\n\n'
                '<b>Что нужно сделать:</b>\n'
                '1. Откройте @BotFather\n'
                '2. Отправьте /mybots\n'
                '3. Выберите вашего бота\n'
                '4. Выберите "Payments" → "Connect YooKassa"\n'
                '5. Следуйте инструкциям для подключения\n\n'
                'После подключения администратор добавит provider_token в настройки.',
                parse_mode='HTML'
            )
        else:
            await callback.message.answer(
                '❌ <b>Ошибка при оформлении подписки</b>\n\n'
                f'Не удалось отправить счет на оплату.\n'
                f'Ошибка: {error_msg}\n\n'
                'Попробуйте позже или обратитесь к администратору.',
                parse_mode='HTML'
            )

# Обработчик успешной подписки
@router.message(lambda msg: msg.successful_payment is not None)
async def process_subscription_payment(message: Message):
    """Обработка успешной оплаты подписки"""
    user_id = message.from_user.id
    payment = message.successful_payment
    
    logger.info(f"[SUBSCRIPTIONS] Обработка успешной оплаты для user_id={user_id}")
    
    # Сохраняем информацию о подписке
    expires_at = datetime.now() + timedelta(days=30)  # 1 месяц
    subscription_data = {
        'active': True,
        'expiresAt': expires_at.isoformat(),
        'subscriptionId': SUBSCRIPTION_ID,
        'paymentDate': datetime.now().isoformat(),
        'invoicePayload': payment.invoice_payload
    }
    
    logger.info(f"[SUBSCRIPTIONS] Сохранение подписки: user_id={user_id}, expires_at={expires_at.isoformat()}")
    save_subscription(user_id, subscription_data)
    logger.info(f"[SUBSCRIPTIONS] Подписка успешно сохранена для user_id={user_id}")
    
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
    await safe_answer_callback(callback)
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

