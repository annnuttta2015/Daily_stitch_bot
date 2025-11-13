from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from data.storage import is_subscribed, get_all_user_ids
from handlers.entries import add_stitches_dialog, show_history
from handlers.statistics import show_statistics
from handlers.projects import show_projects, add_project_dialog
from handlers.keyboards import get_main_menu
from config import ADMIN_IDS
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    from config import TEST_MODE
    
    if not TEST_MODE and not is_subscribed(user_id):
        # Показываем информацию о подписке
        await message.answer(
            '🔒 <b>Дневник вышивальщицы</b>\n\n'
            'Для использования бота необходима подписка.\n\n'
            '💰 <b>Стоимость:</b> 99 рублей в месяц\n\n'
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
    """Показать список ID пользователей (только для администраторов)"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await message.answer('❌ У вас нет доступа к этой команде.')
        return
    
    user_ids = get_all_user_ids()
    
    if not user_ids:
        await message.answer('📝 Пользователей пока нет.')
        return
    
    text = f'<b>👥 Пользователи бота (всего: {len(user_ids)})</b>\n\n'
    
    # Показываем ID по 10 в строке для компактности
    for i in range(0, len(user_ids), 10):
        batch = user_ids[i:i+10]
        text += ' '.join(f'<code>{uid}</code>' for uid in batch) + '\n'
    
    await message.answer(text, parse_mode='HTML')

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    await callback.answer()
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
    await callback.answer()
    await add_stitches_dialog(callback.message, callback.from_user.id)

@router.callback_query(F.data == "my_projects")
async def callback_projects(callback: CallbackQuery):
    await callback.answer()
    await show_projects(callback.message, callback.from_user.id)

@router.callback_query(F.data == "add_project")
async def callback_add_project(callback: CallbackQuery):
    await callback.answer()
    await add_project_dialog(callback.message, callback.from_user.id)

@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery):
    await callback.answer()
    await show_history(callback.message, callback.from_user.id)

