from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from data.storage import is_subscribed, get_all_user_ids, get_user_subscription, grant_access, save_user_id
from handlers.entries import add_stitches_dialog, show_history
from handlers.statistics import show_statistics
from handlers.projects import show_projects, add_project_dialog
from handlers.keyboards import get_main_menu
from config import ADMIN_IDS
from utils import safe_answer_callback
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    from config import TEST_MODE
    
    logger.info(f"[COMMANDS] /start вызван для user_id={user_id}, TEST_MODE={TEST_MODE}")
    
    # Сохраняем ID пользователя (если его еще нет)
    save_user_id(user_id)
    
    # Проверяем, первый ли раз пользователь запускает бота
    existing_subscription = get_user_subscription(user_id)
    is_first_time = existing_subscription is None
    
    subscription_status = is_subscribed(user_id)
    logger.info(f"[COMMANDS] is_subscribed({user_id}) = {subscription_status}, is_first_time={is_first_time}")
    
    # Если первый раз и не в тестовом режиме - выдаем 3 дня пробной подписки
    if is_first_time and not TEST_MODE:
        try:
            expires_at = grant_access(user_id, days=3, is_trial=True)
            logger.info(f"[COMMANDS] Выдана пробная подписка на 3 дня для user_id={user_id}, expires_at={expires_at}")
            
            # Отправляем сообщение о пробной подписке
            await message.answer(
                '🎉 <b>Добро пожаловать!</b>\n\n'
                'Вам предоставлена <b>пробная подписка на 3 дня</b>!\n\n'
                f'Подписка действует до: {expires_at.strftime("%d.%m.%Y")}\n\n'
                'Попробуйте все функции бота:\n'
                '• Добавление крестиков\n'
                '• Статистика и прогресс\n'
                '• Проекты с фото\n'
                '• Челленджи и планы\n'
                '• И многое другое!\n\n'
                'После окончания пробного периода для продолжения использования потребуется оформление подписки (99₽/мес).',
                parse_mode='HTML',
                reply_markup=get_main_menu()
            )
            return
        except Exception as e:
            logger.error(f"[COMMANDS] Ошибка при выдаче пробной подписки для user_id={user_id}: {e}", exc_info=True)
    
    if not TEST_MODE and not subscription_status:
        # Показываем информацию о подписке
        await message.answer(
            '🔒 <b>Дневник вышивальщицы</b>\n\n'
            'Для использования бота необходима подписка.\n\n'
            '💰 <b>Стоимость:</b> 99 рублей в месяц\n\n'
            '📢 <b>Подписывайтесь на канал создателя:</b>\n'
            '<a href="https://t.me/krestiki_dekret">Крестики в декрете</a>\n\n'
            'Используйте кнопку ниже для оформления подписки.',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text='💳 Оформить подписку',
                    callback_data='subscribe'
                )
            ]])
        )
        return
    
    await message.answer(
        '🧵 <b>Дневник вышивальщицы</b>\n\n'
        'Добро пожаловать! Этот бот поможет вам отслеживать прогресс в вышивке крестиком.\n\n'
        '💰 <b>Бот работает по платной подписке: 99 рублей в месяц</b>\n\n'
        '📢 <b>Подписывайтесь на канал создателя:</b>\n'
        '<a href="https://t.me/krestiki_dekret">Крестики в декрете</a>\n\n'
        'Выберите действие:',
        parse_mode='HTML',
        reply_markup=get_main_menu()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        '<b>📖 Помощь</b>\n\n'
        '<b>Основные команды:</b>\n'
        '/start - Главное меню\n'
        '/stats - Быстрая статистика\n'
        '/add - Добавить крестики\n\n'
        '<b>Возможности:</b>\n'
        '• Добавление крестиков за день\n'
        '• Просмотр статистики (день/месяц/год)\n'
        '• Ведение списка работ с фото\n'
        '• Календарь вышивальных дней\n'
        '• Хэштеги для отслеживания работ\n'
        '• Вишлист, заметки и планы/цели\n'
        '• Челленджи и достижения',
        parse_mode='HTML'
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        return
    await show_statistics(message, user_id)

@router.message(Command("add"))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        return
    await add_stitches_dialog(message, user_id)

@router.message(Command("users"))
async def cmd_users(message: Message):
    """Показать статистику по пользователям (только для администраторов)"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return
    
    from data.storage import get_entries, get_projects, get_user_subscription
    
    user_ids = get_all_user_ids()
    
    if not user_ids:
        await message.answer('📝 Пользователей пока нет.')
        return
    
    # Подсчитываем статистику
    total_users = len(user_ids)
    active_subscriptions = 0
    total_entries = 0
    total_projects = 0
    
    for uid in user_ids:
        if get_user_subscription(uid) and is_subscribed(uid):
            active_subscriptions += 1
        entries = get_entries(uid)
        total_entries += len(entries)
        projects = get_projects(uid)
        total_projects += len(projects)
    
    text = f'<b>👥 Статистика пользователей</b>\n\n'
    text += f'📊 Всего пользователей: <b>{total_users}</b>\n'
    text += f'✅ Активных подписок: <b>{active_subscriptions}</b>\n'
    text += f'📝 Всего записей о крестиках: <b>{total_entries}</b>\n'
    text += f'🖼️ Всего проектов: <b>{total_projects}</b>\n\n'
    
    if total_users <= 20:
        # Если пользователей немного, показываем ID
        text += '<b>ID пользователей:</b>\n'
        for i in range(0, len(user_ids), 10):
            batch = user_ids[i:i+10]
            text += ' '.join(f'<code>{uid}</code>' for uid in batch) + '\n'
    else:
        # Если много, показываем только первые 10
        text += f'<b>Первые 10 ID:</b>\n'
        text += ' '.join(f'<code>{uid}</code>' for uid in user_ids[:10]) + '\n'
        text += f'<i>... и еще {total_users - 10} пользователей</i>'
    
    await message.answer(text, parse_mode='HTML')

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    await safe_answer_callback(callback)
    # Очищаем все незавершенные диалоги при переходе в главное меню
    user_id = callback.from_user.id
    from handlers import entries, projects, delete, wishlist, notes, plans
    entries.clear_pending(user_id)
    projects.clear_pending_project(user_id)
    delete.clear_pending_delete(user_id)
    wishlist.clear_pending_wishlist(user_id)
    notes.clear_pending_note(user_id)
    plans.clear_pending_plan(user_id)
    
    text = (
        '🧵 <b>Дневник вышивальщицы</b>\n\n'
        'Выберите действие:'
    )
    
    # Проверяем, есть ли у сообщения фото
    if callback.message.photo:
        # Если есть фото, отправляем новое текстовое сообщение
        try:
            await callback.message.answer(
                text,
                parse_mode='HTML',
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logger.error(f"Error in callback_main_menu: {e}")
    else:
        # Если фото нет, редактируем текст
        try:
            await callback.message.edit_text(
                text,
                parse_mode='HTML',
                reply_markup=get_main_menu()
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое
            try:
                await callback.message.answer(
                    text,
                    parse_mode='HTML',
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                logger.error(f"Error in callback_main_menu: {e}")

@router.callback_query(F.data == "add_stitches")
async def callback_add_stitches(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await add_stitches_dialog(callback.message, callback.from_user.id)

@router.callback_query(F.data == "my_projects")
async def callback_projects(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await show_projects(callback.message, callback.from_user.id)

@router.callback_query(F.data == "add_project")
async def callback_add_project(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await add_project_dialog(callback.message, callback.from_user.id)

@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await show_history(callback.message, callback.from_user.id)

