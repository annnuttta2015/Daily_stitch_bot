from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from datetime import datetime
import json
import os
import tempfile
from data.storage import (
    get_entries, get_projects, get_wishlist, get_notes, get_plans,
    get_user_challenges, get_user_subscription
)
from utils import safe_answer_callback
from handlers.keyboards import get_back_keyboard

router = Router()

async def export_user_data(message: Message, user_id: int):
    """Экспортировать все данные пользователя в JSON"""
    try:
        # Собираем все данные пользователя
        export_data = {
            'userId': user_id,
            'exportDate': datetime.now().isoformat(),
            'entries': get_entries(user_id),
            'projects': get_projects(user_id),
            'wishlist': get_wishlist(user_id),
            'notes': get_notes(user_id),
            'plans': get_plans(user_id),
            'challenges': get_user_challenges(user_id),
            'subscription': get_user_subscription(user_id)
        }
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json', delete=False) as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
            temp_file_path = f.name
        
        # Отправляем файл
        file = FSInputFile(temp_file_path, filename=f'export_{user_id}_{datetime.now().strftime("%Y%m%d")}.json')
        await message.answer_document(
            file,
            caption='📥 <b>Экспорт данных</b>\n\nВсе ваши данные сохранены в JSON файле.',
            parse_mode='HTML'
        )
        
        # Удаляем временный файл
        try:
            os.unlink(temp_file_path)
        except:
            pass
            
    except Exception as e:
        await message.answer(
            f'❌ Ошибка при экспорте данных: {str(e)}',
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data == "export_data")
async def callback_export_data(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await export_user_data(callback.message, callback.from_user.id)


