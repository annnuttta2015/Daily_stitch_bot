from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Клавиатура главного меню
def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text='➕ Добавить крестики', callback_data='add_stitches'),
            InlineKeyboardButton(text='📊 Статистика', callback_data='statistics'),
        ],
        [
            InlineKeyboardButton(text='📅 Календарь', callback_data='calendar_menu'),
            InlineKeyboardButton(text='#️⃣ Хэштеги', callback_data='hashtags_menu'),
        ],
        [
            InlineKeyboardButton(text='📝 Мои работы', callback_data='my_projects'),
            InlineKeyboardButton(text='➕ Новая работа', callback_data='add_project'),
        ],
        [
            InlineKeyboardButton(text='📋 Планы/Цели', callback_data='plans_menu'),
            InlineKeyboardButton(text='📝 Заметки', callback_data='notes_menu'),
        ],
        [
            InlineKeyboardButton(text='🎁 Вишлист', callback_data='wishlist_menu'),
        ],
        [
            InlineKeyboardButton(text='🏆 Челленджи', callback_data='challenges_menu'),
        ],
        [
            InlineKeyboardButton(text='💳 Подписка', callback_data='subscribe'),
        ],
        [
            InlineKeyboardButton(text='🗑️ Удалить данные', callback_data='delete_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура "Назад"
def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')
    ]])

# Клавиатура для навигации по работам
def get_project_navigation(current_index: int, total: int, project_id: str = None, has_photo: bool = False) -> InlineKeyboardMarkup:
    keyboard = []
    nav_buttons = []
    
    if total > 1:
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'project_prev_{current_index}'))
        if current_index < total - 1:
            nav_buttons.append(InlineKeyboardButton(text='Вперед ➡️', callback_data=f'project_next_{current_index}'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки для работы с фото
    if project_id:
        photo_buttons = []
        if has_photo:
            photo_buttons.append(InlineKeyboardButton(text='🔄 Изменить фото', callback_data=f'project_change_photo_{project_id}'))
            photo_buttons.append(InlineKeyboardButton(text='🗑️ Удалить фото', callback_data=f'project_delete_photo_{project_id}'))
        else:
            photo_buttons.append(InlineKeyboardButton(text='➕ Добавить фото', callback_data=f'project_change_photo_{project_id}'))
        
        if photo_buttons:
            keyboard.append(photo_buttons)
        
        # Кнопка удаления проекта
        keyboard.append([InlineKeyboardButton(text='🗑️ Удалить работу', callback_data=f'project_delete_{project_id}')])
    
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура меню удаления
def get_delete_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text='🗑️ Удалить всё', callback_data='delete_all'),
            InlineKeyboardButton(text='📅 Удалить день', callback_data='delete_day'),
        ],
        [
            InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

