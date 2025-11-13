from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from data.storage import get_entries, format_number
from handlers.keyboards import get_back_keyboard

router = Router()

async def show_period_comparison(message: Message, user_id: int):
    """Показать сравнение периодов"""
    entries = get_entries(user_id)
    now = datetime.now()
    
    # Текущий месяц
    current_month_start = datetime(now.year, now.month, 1).date()
    current_month_str = current_month_start.strftime('%Y-%m-%d')
    
    # Предыдущий месяц
    if now.month == 1:
        prev_month_start = datetime(now.year - 1, 12, 1).date()
    else:
        prev_month_start = datetime(now.year, now.month - 1, 1).date()
    
    # Последний день предыдущего месяца
    if now.month == 1:
        prev_month_end = datetime(now.year - 1, 12, 31).date()
    else:
        from calendar import monthrange
        prev_month_end = datetime(now.year, now.month - 1, monthrange(now.year, now.month - 1)[1]).date()
    
    prev_month_start_str = prev_month_start.strftime('%Y-%m-%d')
    prev_month_end_str = prev_month_end.strftime('%Y-%m-%d')
    
    # Текущий год
    current_year_start = datetime(now.year, 1, 1).date()
    current_year_str = current_year_start.strftime('%Y-%m-%d')
    
    # Предыдущий год
    prev_year_start = datetime(now.year - 1, 1, 1).date()
    prev_year_end = datetime(now.year - 1, 12, 31).date()
    prev_year_start_str = prev_year_start.strftime('%Y-%m-%d')
    prev_year_end_str = prev_year_end.strftime('%Y-%m-%d')
    
    # Подсчет для текущего месяца
    current_month_entries = [e for e in entries if e.get('date') >= current_month_str]
    current_month_count = sum(e.get('count', 0) for e in current_month_entries)
    current_month_days = len(set(e.get('date') for e in current_month_entries))
    
    # Подсчет для предыдущего месяца
    prev_month_entries = [e for e in entries if prev_month_start_str <= e.get('date') <= prev_month_end_str]
    prev_month_count = sum(e.get('count', 0) for e in prev_month_entries)
    prev_month_days = len(set(e.get('date') for e in prev_month_entries))
    
    # Подсчет для текущего года
    current_year_entries = [e for e in entries if e.get('date') >= current_year_str]
    current_year_count = sum(e.get('count', 0) for e in current_year_entries)
    current_year_days = len(set(e.get('date') for e in current_year_entries))
    
    # Подсчет для предыдущего года
    prev_year_entries = [e for e in entries if prev_year_start_str <= e.get('date') <= prev_year_end_str]
    prev_year_count = sum(e.get('count', 0) for e in prev_year_entries)
    prev_year_days = len(set(e.get('date') for e in prev_year_entries))
    
    # Формируем текст
    text = '<b>📊 Сравнение периодов</b>\n\n'
    
    # Сравнение месяцев
    text += '<b>📅 Месяцы:</b>\n'
    text += f'Текущий месяц: {format_number(current_month_count)} крестиков ({current_month_days} дней)\n'
    text += f'Предыдущий месяц: {format_number(prev_month_count)} крестиков ({prev_month_days} дней)\n'
    
    if prev_month_count > 0:
        month_diff = current_month_count - prev_month_count
        month_percent = (month_diff / prev_month_count * 100) if prev_month_count > 0 else 0
        if month_diff > 0:
            text += f'📈 <b>+{format_number(month_diff)}</b> крестиков ({month_percent:+.1f}%)\n'
        elif month_diff < 0:
            text += f'📉 <b>{format_number(month_diff)}</b> крестиков ({month_percent:+.1f}%)\n'
        else:
            text += f'➡️ Без изменений\n'
    else:
        text += f'📈 <b>+{format_number(current_month_count)}</b> крестиков (новый период)\n'
    
    text += '\n'
    
    # Сравнение годов
    text += '<b>📆 Годы:</b>\n'
    text += f'Текущий год: {format_number(current_year_count)} крестиков ({current_year_days} дней)\n'
    text += f'Предыдущий год: {format_number(prev_year_count)} крестиков ({prev_year_days} дней)\n'
    
    if prev_year_count > 0:
        year_diff = current_year_count - prev_year_count
        year_percent = (year_diff / prev_year_count * 100) if prev_year_count > 0 else 0
        if year_diff > 0:
            text += f'📈 <b>+{format_number(year_diff)}</b> крестиков ({year_percent:+.1f}%)\n'
        elif year_diff < 0:
            text += f'📉 <b>{format_number(year_diff)}</b> крестиков ({year_percent:+.1f}%)\n'
        else:
            text += f'➡️ Без изменений\n'
    else:
        text += f'📈 <b>+{format_number(current_year_count)}</b> крестиков (новый период)\n'
    
    await message.answer(text, parse_mode='HTML', reply_markup=get_back_keyboard())

@router.callback_query(F.data == "period_comparison")
async def callback_period_comparison(callback: CallbackQuery):
    await callback.answer()
    await show_period_comparison(callback.message, callback.from_user.id)


