from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from dateutil import parser
from data.storage import delete_all_user_data, delete_entry_by_date, get_entries
from handlers.keyboards import get_delete_menu, get_back_keyboard
from utils import safe_answer_callback

router = Router()

# Состояния для диалога удаления
pending_deletes = {}

@router.callback_query(F.data == "delete_menu")
async def callback_delete_menu(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await callback.message.edit_text(
        '🗑️ <b>Удаление данных</b>\n\n'
        'Выберите что удалить:',
        parse_mode='HTML',
        reply_markup=get_delete_menu()
    )

@router.callback_query(F.data == "delete_all")
async def callback_delete_all(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    
    # Запрашиваем подтверждение
    keyboard = [
        [
            InlineKeyboardButton(text='✅ Да, удалить всё', callback_data='confirm_delete_all'),
            InlineKeyboardButton(text='❌ Отмена', callback_data='delete_menu'),
        ],
    ]
    await callback.message.edit_text(
        '⚠️ <b>ВНИМАНИЕ!</b>\n\n'
        'Вы уверены, что хотите удалить ВСЕ свои данные?\n\n'
        'Будут удалены:\n'
        '• Все записи о крестиках\n'
        '• Все проекты и фото\n'
        '• Вишлист, заметки, планы/цели\n'
        '• Челленджи\n\n'
        '⚠️ Это действие нельзя отменить!\n'
        'ℹ️ Ваш ID и подписка останутся для сохранения доступа к боту.',
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "confirm_delete_all")
async def callback_confirm_delete_all(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    delete_all_user_data(user_id)
    await callback.message.edit_text(
        '✅ <b>Все данные удалены!</b>',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "delete_day")
async def callback_delete_day(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    pending_deletes[user_id] = {'step': 'date'}
    await callback.message.edit_text(
        '📅 <b>Удаление записи за день</b>\n\n'
        'Введите дату в формате ДД.ММ.ГГГГ (или "сегодня"):',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )

async def process_delete_message(message: Message, user_id: int):
    if user_id not in pending_deletes:
        return False
    
    state = pending_deletes[user_id]
    
    if state['step'] == 'date':
        text = message.text.strip().lower()
        
        if text == 'сегодня' or text == 'today':
            date = datetime.now().strftime('%Y-%m-%d')
            date_obj = datetime.now()
        else:
            try:
                date_obj = parser.parse(message.text, dayfirst=True)
                date = date_obj.strftime('%Y-%m-%d')
            except:
                await message.answer('❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или "сегодня"', reply_markup=get_back_keyboard())
                return True
        
        # Проверяем, есть ли запись за эту дату
        entries = get_entries(user_id)
        entry_for_date = [e for e in entries if e.get('date') == date]
        
        # Если не найдено, пробуем найти запись с некорректной датой, которая может совпадать с введенным текстом
        if not entry_for_date and text != 'сегодня' and text != 'today':
            # Пробуем найти запись, где дата может быть в формате, который пользователь ввел
            original_text = message.text.strip()
            for e in entries:
                entry_date = e.get('date', '')
                # Проверяем прямое совпадение или совпадение после преобразования
                if entry_date == original_text or entry_date == date:
                    entry_for_date = [e]
                    # Используем дату из записи для удаления
                    date = entry_date
                    break
        
        if not entry_for_date:
            date_str = date_obj.strftime('%d.%m.%Y') if text != 'сегодня' else 'сегодня'
            await message.answer(
                f'❌ Нет записи за {date_str}',
                reply_markup=get_back_keyboard()
            )
            del pending_deletes[user_id]
            return True
        
        delete_entry_by_date(date, user_id)
        
        # Безопасное форматирование даты для отображения
        try:
            date_str = datetime.strptime(date, '%Y-%m-%d').strftime('%d %B %Y')
        except (ValueError, TypeError):
            # Если дата некорректная (например, 622-11-27), показываем в упрощенном формате
            try:
                # Пробуем разобрать дату вручную
                parts = date.split('-')
                if len(parts) == 3:
                    date_str = f"{parts[2]}.{parts[1]}.{parts[0]}"
                else:
                    date_str = date.replace('-', '.')
            except:
                date_str = date
        
        await message.answer(
            f'✅ <b>Запись удалена!</b>\n\n'
            f'Дата: {date_str}',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        del pending_deletes[user_id]
        return True
    
    return False

def clear_pending_delete(user_id: int):
    if user_id in pending_deletes:
        del pending_deletes[user_id]

