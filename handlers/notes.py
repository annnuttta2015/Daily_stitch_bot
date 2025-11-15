from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from data.storage import get_notes, save_note, delete_note
from handlers.keyboards import get_back_keyboard
from utils import safe_answer_callback

router = Router()

pending_notes = {}

async def show_notes(message: Message, user_id: int):
    """Показать список заметок"""
    notes = get_notes(user_id)
    notes.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    
    if not notes:
        keyboard = [
            [InlineKeyboardButton(text='➕ Добавить заметку', callback_data='note_add')],
            [InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')]
        ]
        await message.answer(
            '📝 <b>Заметки</b>\n\n'
            'У вас пока нет заметок. Добавьте первую!',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
    
    text = '<b>📝 Ваши заметки:</b>\n\n'
    keyboard = []
    
    for i, note in enumerate(notes[:20], 1):  # Показываем до 20 заметок
        title = note.get('title', 'Без названия')
        preview = note.get('text', '')[:30]
        if len(note.get('text', '')) > 30:
            preview += "..."
        text += f"{i}. <b>{title}</b>\n{preview}\n\n"
        keyboard.append([InlineKeyboardButton(
            text=f"📄 {title[:30]}",
            callback_data=f"note_{note.get('id')}"
        )])
    
    keyboard.append([InlineKeyboardButton(text='➕ Добавить заметку', callback_data='note_add')])
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def add_note_dialog(message: Message, user_id: int):
    """Начать диалог добавления заметки"""
    await message.answer(
        '📝 <b>Добавление заметки</b>\n\n'
        'Введите название заметки:',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )
    pending_notes[user_id] = {'step': 'title'}

async def process_note_message(message: Message, user_id: int):
    """Обработать сообщение для заметки"""
    if user_id not in pending_notes:
        return False
    
    state = pending_notes[user_id]
    
    if state['step'] == 'title':
        title = message.text.strip()
        if not title:
            await message.answer('❌ Название не может быть пустым', reply_markup=get_back_keyboard())
            return True
        
        state['title'] = title
        state['step'] = 'text'
        await message.answer(
            f'✅ <b>Название:</b> {title}\n\n'
            '✍️ <b>Шаг 2: Введите текст заметки</b>\n\n'
            'Просто отправьте текст заметки.',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        return True
    
    elif state['step'] == 'text':
        text = message.text.strip()
        if not text:
            await message.answer('❌ Текст не может быть пустым', reply_markup=get_back_keyboard())
            return True
        
        note = {
            'id': f"note-{user_id}-{int(datetime.now().timestamp())}",
            'title': state['title'],
            'text': text,
            'userId': user_id,
            'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        save_note(note)
        await message.answer(
            f'✅ <b>Заметка сохранена!</b>\n\n'
            f'<b>{note["title"]}</b>\n'
            f'{text[:100]}...' if len(text) > 100 else text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        del pending_notes[user_id]
        return True
    
    return False

async def show_note(message: Message, user_id: int, note_id: str):
    """Показать заметку"""
    notes = get_notes(user_id)
    note = next((n for n in notes if n.get('id') == note_id), None)
    
    if not note:
        await message.answer('❌ Заметка не найдена', reply_markup=get_back_keyboard())
        return
    
    created = note.get('createdAt', 'Неизвестно')
    text = (
        f'<b>📄 {note.get("title")}</b>\n\n'
        f'{note.get("text", "")}\n\n'
        f'<i>Создано: {created}</i>'
    )
    
    keyboard = [
        [InlineKeyboardButton(text='🗑️ Удалить', callback_data=f"note_delete_{note_id}")],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='notes_menu')]
    ]
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "notes_menu")
async def callback_notes_menu(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await show_notes(callback.message, callback.from_user.id)

@router.callback_query(F.data == "note_add")
async def callback_note_add(callback: CallbackQuery):
    await safe_answer_callback(callback, "Введите название заметки в следующем сообщении")
    try:
        await callback.message.edit_text(
            '📝 <b>Добавление заметки</b>\n\n'
            '✍️ <b>Шаг 1: Введите название заметки</b>\n\n'
            'Просто отправьте текст с названием заметки.',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    except:
        await callback.message.answer(
            '📝 <b>Добавление заметки</b>\n\n'
            '✍️ <b>Шаг 1: Введите название заметки</b>\n\n'
            'Просто отправьте текст с названием заметки.',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    pending_notes[callback.from_user.id] = {'step': 'title'}

@router.callback_query(F.data.startswith("note_"))
async def callback_note(callback: CallbackQuery):
    await safe_answer_callback(callback)
    note_id = callback.data.replace("note_", "")
    if note_id.startswith("delete_"):
        note_id = note_id.replace("delete_", "")
        delete_note(note_id, callback.from_user.id)
        await callback.message.answer('✅ Заметка удалена', reply_markup=get_back_keyboard())
        await show_notes(callback.message, callback.from_user.id)
    else:
        await show_note(callback.message, callback.from_user.id, note_id)

def clear_pending_note(user_id: int):
    if user_id in pending_notes:
        del pending_notes[user_id]

