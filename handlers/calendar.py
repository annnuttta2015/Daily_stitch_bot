from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from calendar import monthrange
from data.storage import get_entries, format_number
from handlers.keyboards import get_back_keyboard

router = Router()

def generate_calendar(year: int, month: int, user_id: int) -> str:
    """Генерировать календарь с отметками вышивальных дней"""
    entries = get_entries(user_id)
    
    # Создаем словарь дат с количеством крестиков
    dates_data = {}
    for entry in entries:
        date_str = entry.get('date', '')
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d')
            if entry_date.year == year and entry_date.month == month:
                day = entry_date.day
                if day not in dates_data:
                    dates_data[day] = 0
                dates_data[day] += entry.get('count', 0)
        except:
            continue
    
    # Названия месяцев
    months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
              'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    
    month_name = months[month - 1]
    
    # Заголовок
    text = f'<b>📅 {month_name} {year}</b>\n\n'
    
    # Дни недели
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    weekday_line = '  '.join(f'{wd:>3}' for wd in weekdays)
    
    # Первый день месяца и количество дней
    first_day = datetime(year, month, 1)
    first_weekday = first_day.weekday()  # 0 = понедельник
    days_in_month = monthrange(year, month)[1]
    
    # Создаем календарь построчно
    calendar_lines = []
    current_line = []
    
    # Отступ для первого дня
    for _ in range(first_weekday):
        current_line.append('   ')  # 3 пробела
    
    total_days = 0
    total_stitches = 0
    
    for day in range(1, days_in_month + 1):
        if day in dates_data:
            # День с вышивкой - используем символ ●
            count = dates_data[day]
            total_days += 1
            total_stitches += count
            day_str = f'●{day:2d}'
            current_line.append(day_str)
        else:
            # День без вышивки
            day_str = f' {day:2d}'
            current_line.append(day_str)
        
        # Перенос строки в конце недели (7 дней)
        if len(current_line) == 7:
            calendar_lines.append('  '.join(current_line))
            current_line = []
    
    # Добавляем оставшиеся дни последней недели
    if current_line:
        # Дополняем до 7 элементов пробелами для выравнивания
        while len(current_line) < 7:
            current_line.append('   ')
        calendar_lines.append('  '.join(current_line))
    
    # Добавляем календарь в текст с моноширинным шрифтом
    text += f'<code>{weekday_line}\n'
    text += '\n'.join(calendar_lines) + '</code>\n\n'
    text += '<i>● - день с вышивкой</i>'
    
    # Статистика месяца
    text += f'\n<b>Статистика:</b>\n'
    text += f'📊 Дней с вышивкой: {total_days}\n'
    text += f'✨ Всего крестиков: {format_number(total_stitches)}\n'
    if total_days > 0:
        avg = total_stitches // total_days
        text += f'📈 Среднее в день: {format_number(avg)}'
    
    return text

async def show_calendar(message: Message, user_id: int, year: int = None, month: int = None):
    """Показать календарь"""
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    calendar_text = generate_calendar(year, month, user_id)
    
    # Кнопки навигации
    keyboard = []
    nav_buttons = []
    
    # Предыдущий месяц
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    nav_buttons.append(InlineKeyboardButton(
        text='⬅️',
        callback_data=f"calendar_{prev_year}_{prev_month}"
    ))
    
    # Текущий месяц
    nav_buttons.append(InlineKeyboardButton(
        text='📅 Сегодня',
        callback_data=f"calendar_{now.year}_{now.month}"
    ))
    
    # Следующий месяц
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    nav_buttons.append(InlineKeyboardButton(
        text='➡️',
        callback_data=f"calendar_{next_year}_{next_month}"
    ))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    await message.answer(
        calendar_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "calendar_menu")
async def callback_calendar_menu(callback: CallbackQuery):
    await callback.answer()
    now = datetime.now()
    calendar_text = generate_calendar(now.year, now.month, callback.from_user.id)
    
    # Кнопки навигации
    keyboard = []
    nav_buttons = []
    
    # Предыдущий месяц
    prev_month = now.month - 1
    prev_year = now.year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    nav_buttons.append(InlineKeyboardButton(
        text='⬅️',
        callback_data=f"calendar_{prev_year}_{prev_month}"
    ))
    
    # Текущий месяц
    nav_buttons.append(InlineKeyboardButton(
        text='📅 Сегодня',
        callback_data=f"calendar_{now.year}_{now.month}"
    ))
    
    # Следующий месяц
    next_month = now.month + 1
    next_year = now.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    nav_buttons.append(InlineKeyboardButton(
        text='➡️',
        callback_data=f"calendar_{next_year}_{next_month}"
    ))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    try:
        await callback.message.edit_text(
            calendar_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    except:
        await callback.message.answer(
            calendar_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@router.callback_query(F.data.startswith("calendar_"))
async def callback_calendar(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.replace("calendar_", "").split("_")
    if len(parts) == 2:
        year = int(parts[0])
        month = int(parts[1])
        calendar_text = generate_calendar(year, month, callback.from_user.id)
        
        # Кнопки навигации
        keyboard = []
        nav_buttons = []
        now = datetime.now()
        
        # Предыдущий месяц
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        nav_buttons.append(InlineKeyboardButton(
            text='⬅️',
            callback_data=f"calendar_{prev_year}_{prev_month}"
        ))
        
        # Текущий месяц
        nav_buttons.append(InlineKeyboardButton(
            text='📅 Сегодня',
            callback_data=f"calendar_{now.year}_{now.month}"
        ))
        
        # Следующий месяц
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        nav_buttons.append(InlineKeyboardButton(
            text='➡️',
            callback_data=f"calendar_{next_year}_{next_month}"
        ))
        
        keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
        
        try:
            await callback.message.edit_text(
                calendar_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except:
            await callback.message.answer(
                calendar_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )

