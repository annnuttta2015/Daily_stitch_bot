from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from data.storage import get_wishlist, add_to_wishlist, remove_from_wishlist, update_wishlist_item
from handlers.keyboards import get_back_keyboard

router = Router()

pending_wishlist = {}

async def show_wishlist(message: Message, user_id: int):
    """Показать вишлист"""
    items = get_wishlist(user_id)
    
    if not items:
        keyboard = [
            [InlineKeyboardButton(text='➕ Добавить', callback_data='wishlist_add')],
            [InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')]
        ]
        await message.answer(
            '📝 <b>Вишлист</b>\n\n'
            'Ваш вишлист пуст. Добавьте первую работу!',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
    
    text = '<b>📝 Ваш вишлист:</b>\n\n'
    keyboard = []
    
    for i, item in enumerate(items, 1):
        name = item.get('name', 'Без названия')
        status = "✅ Выполнено" if item.get('completed', False) else "⏳ В планах"
        text += f"{i}. {name} - {status}\n"
        keyboard.append([InlineKeyboardButton(
            text=f"{'✅' if item.get('completed') else '⏳'} {name[:30]}",
            callback_data=f"wishlist_item_{item.get('id')}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text='➕ Добавить', callback_data='wishlist_add'),
        InlineKeyboardButton(text='📤 Поделиться', callback_data='wishlist_share')
    ])
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def add_wishlist_dialog(message: Message, user_id: int):
    """Начать диалог добавления в вишлист"""
    await message.answer(
        '📝 <b>Добавление в вишлист</b>\n\n'
        'Введите название работы:',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )
    pending_wishlist[user_id] = {'step': 'name'}

async def process_wishlist_message(message: Message, user_id: int):
    """Обработать сообщение для вишлиста"""
    if user_id not in pending_wishlist:
        return False
    
    state = pending_wishlist[user_id]
    
    if state['step'] == 'name':
        name = message.text.strip()
        if not name:
            await message.answer('❌ Название не может быть пустым')
            return True
        
        state['name'] = name
        state['step'] = 'link'
        await message.answer(
            f'✅ Название: {name}\n\n'
            '🔗 <b>Шаг 2: Добавить ссылку (опционально)</b>\n\n'
            'Отправьте ссылку на товар или отправьте "пропустить"',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        return True
    
    elif state['step'] == 'link':
        link_input = message.text.strip()
        link_lower = link_input.lower()
        
        # Проверяем, пропустил ли пользователь
        if link_lower == 'пропустить' or link_lower == 'skip' or not link_input:
            link = None
        else:
            # Сохраняем оригинальную ссылку (без .lower())
            link = link_input
            # Проверяем, что это похоже на ссылку
            if not (link.lower().startswith('http://') or link.lower().startswith('https://')):
                # Если нет протокола, добавляем https://
                if '.' in link and not link.lower().startswith('www.'):
                    link = f'https://{link}'
                elif link.lower().startswith('www.'):
                    link = f'https://{link}'
                else:
                    # Если не похоже на ссылку, спрашиваем еще раз
                    await message.answer(
                        '❌ Неверный формат ссылки.\n\n'
                        'Отправьте ссылку (например: https://ozon.ru/...) или "пропустить"',
                        reply_markup=get_back_keyboard()
                    )
                    return True
        
        item = {
            'id': f"wishlist-{user_id}-{int(datetime.now().timestamp())}",
            'name': state['name'],
            'userId': user_id,
            'createdAt': datetime.now().strftime('%Y-%m-%d'),
            'completed': False
        }
        
        if link:
            item['link'] = link
        
        add_to_wishlist(item)
        
        result_text = (
            f'✅ <b>Добавлено в вишлист!</b>\n\n'
            f'Название: {state["name"]}'
        )
        if link:
            result_text += f'\n🔗 Ссылка: {link}'
        
        await message.answer(
            result_text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        del pending_wishlist[user_id]
        return True
    
    return False

async def show_wishlist_item(message: Message, user_id: int, item_id: str):
    """Показать детали элемента вишлиста"""
    items = get_wishlist(user_id)
    item = next((i for i in items if i.get('id') == item_id), None)
    
    if not item:
        await message.answer('❌ Элемент не найден', reply_markup=get_back_keyboard())
        return
    
    status = "✅ Выполнено" if item.get('completed', False) else "⏳ В планах"
    created = datetime.strptime(item.get('createdAt', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').strftime('%d.%m.%Y')
    
    text = (
        f'<b>📝 {item.get("name")}</b>\n\n'
        f'Статус: {status}\n'
        f'Добавлено: {created}'
    )
    
    if item.get('link'):
        text += f'\n🔗 <a href="{item.get("link")}">Ссылка на товар</a>'
    
    keyboard = []
    if not item.get('completed', False):
        keyboard.append([InlineKeyboardButton(
            text='✅ Отметить выполненным',
            callback_data=f"wishlist_complete_{item_id}"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text='⏳ Вернуть в планы',
            callback_data=f"wishlist_uncomplete_{item_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text='🗑️ Удалить',
        callback_data=f"wishlist_delete_{item_id}"
    )])
    keyboard.append([InlineKeyboardButton(text='🔙 Назад', callback_data='wishlist_menu')])
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

def get_wishlist_share_text(user_id: int, use_html: bool = True) -> str:
    """Получить текст вишлиста для шаринга (только работы в планах)"""
    items = get_wishlist(user_id)
    
    # Фильтруем только работы в планах
    pending_items = [item for item in items if not item.get('completed', False)]
    
    if not pending_items:
        return "🎁 <b>Мой вишлист </b>\n\nНет работ в планах" if use_html else "🎁 Мой вишлист вышивки\n\nНет работ в планах"
    
    if use_html:
        text = "🎁 <b>Мой вишлист </b>\n\n"
        text += f"⏳ <b>В планах ({len(pending_items)}):</b>\n\n"
    else:
        text = "🎁 Мой вишлист \n\n"
        text += f"⏳ В планах ({len(pending_items)}):\n\n"
    
    # Показываем только работы в планах
    for i, item in enumerate(pending_items, 1):
        name = item.get('name', 'Без названия')
        link = item.get('link', '')
        if link and use_html:
            text += f"{i}. <a href=\"{link}\">{name}</a>\n"
        elif link:
            text += f"{i}. {name} - {link}\n"
        else:
            text += f"{i}. {name}\n"
    
    return text

@router.callback_query(F.data == "wishlist_menu")
async def callback_wishlist_menu(callback: CallbackQuery):
    await callback.answer()
    await show_wishlist(callback.message, callback.from_user.id)

@router.callback_query(F.data == "wishlist_add")
async def callback_wishlist_add(callback: CallbackQuery):
    await callback.answer("Введите название работы в следующем сообщении")
    try:
        await callback.message.edit_text(
            '📝 <b>Добавление в вишлист</b>\n\n'
            '✍️ <b>Шаг 1: Введите название работы</b>\n\n'
            'Просто отправьте текст с названием работы.',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    except:
        await callback.message.answer(
            '📝 <b>Добавление в вишлист</b>\n\n'
            '✍️ <b>Шаг 1: Введите название работы</b>\n\n'
            'Просто отправьте текст с названием работы.',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    pending_wishlist[callback.from_user.id] = {'step': 'name'}

@router.callback_query(F.data.startswith("wishlist_item_"))
async def callback_wishlist_item(callback: CallbackQuery):
    await callback.answer()
    item_id = callback.data.replace("wishlist_item_", "")
    await show_wishlist_item(callback.message, callback.from_user.id, item_id)

@router.callback_query(F.data.startswith("wishlist_complete_"))
async def callback_wishlist_complete(callback: CallbackQuery):
    await callback.answer()
    item_id = callback.data.replace("wishlist_complete_", "")
    update_wishlist_item(item_id, callback.from_user.id, {'completed': True, 'completedAt': datetime.now().strftime('%Y-%m-%d')})
    await show_wishlist_item(callback.message, callback.from_user.id, item_id)

@router.callback_query(F.data.startswith("wishlist_uncomplete_"))
async def callback_wishlist_uncomplete(callback: CallbackQuery):
    await callback.answer()
    item_id = callback.data.replace("wishlist_uncomplete_", "")
    update_wishlist_item(item_id, callback.from_user.id, {'completed': False})
    await show_wishlist_item(callback.message, callback.from_user.id, item_id)

@router.callback_query(F.data.startswith("wishlist_delete_"))
async def callback_wishlist_delete(callback: CallbackQuery):
    await callback.answer()
    item_id = callback.data.replace("wishlist_delete_", "")
    remove_from_wishlist(item_id, callback.from_user.id)
    await callback.message.answer('✅ Удалено из вишлиста', reply_markup=get_back_keyboard())
    await show_wishlist(callback.message, callback.from_user.id)

@router.callback_query(F.data == "wishlist_share")
async def callback_wishlist_share(callback: CallbackQuery):
    await callback.answer()
    items = get_wishlist(callback.from_user.id)
    
    if not items:
        await callback.message.answer(
            '❌ Вишлист пуст. Нечего делиться.',
            reply_markup=get_back_keyboard()
        )
        return
    
    share_text = get_wishlist_share_text(callback.from_user.id, use_html=True)
    
    # Создаем красивую клавиатуру
    keyboard = [
        [InlineKeyboardButton(text='🔙 Назад', callback_data='wishlist_menu')]
    ]
    
    # Отправляем красиво оформленное сообщение
    await callback.message.answer(
        share_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        disable_web_page_preview=False
    )

def clear_pending_wishlist(user_id: int):
    if user_id in pending_wishlist:
        del pending_wishlist[user_id]

