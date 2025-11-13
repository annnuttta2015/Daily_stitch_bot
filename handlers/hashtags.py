from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from data.storage import get_all_hashtags, get_entries_by_hashtag, get_projects_by_hashtag, get_projects, format_number
from handlers.keyboards import get_back_keyboard

router = Router()

async def show_hashtags_menu(message: Message, user_id: int):
    """Показать меню хэштегов"""
    hashtags = get_all_hashtags(user_id)
    
    if not hashtags:
        await message.answer(
            '📝 <b>Хэштеги</b>\n\n'
            'У вас пока нет записей и работ с хэштегами.\n\n'
            'Добавьте хэштег:\n'
            '• При добавлении крестиков\n'
            '• При добавлении работы с фото',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        return
    
    text = '<b>📝 Ваши хэштеги:</b>\n\n'
    keyboard = []
    
    for hashtag in hashtags:
        entries = get_entries_by_hashtag(hashtag, user_id)
        projects = get_projects_by_hashtag(hashtag, user_id)
        total = sum(e.get('count', 0) for e in entries)
        
        # Формируем описание
        desc_parts = []
        if total > 0:
            desc_parts.append(f"{format_number(total)} крестиков")
        if len(entries) > 0:
            desc_parts.append(f"{len(entries)} записей")
        if len(projects) > 0:
            desc_parts.append(f"{len(projects)} фото")
        
        desc = " • ".join(desc_parts) if desc_parts else "нет данных"
        text += f"#{hashtag}: {desc}\n"
        
        # Формируем текст кнопки
        button_text = f"#{hashtag}"
        if total > 0:
            button_text += f" ({format_number(total)})"
        if len(projects) > 0:
            button_text += f" 📸{len(projects)}"
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"hashtag_{hashtag}"
        )])
    
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def show_hashtag_progress(message: Message, user_id: int, hashtag: str):
    """Показать прогресс по хэштегу с фото работ"""
    entries = get_entries_by_hashtag(hashtag, user_id)
    projects = get_projects_by_hashtag(hashtag, user_id)
    
    if not entries and not projects:
        await message.answer(
            f'❌ Нет записей и работ с хэштегом #{hashtag}',
            reply_markup=get_back_keyboard()
        )
        return
    
    # Формируем текст статистики
    text = f'<b>📊 Прогресс по хэштегу #{hashtag}</b>\n\n'
    
    if entries:
        entries.sort(key=lambda x: x.get('date', ''), reverse=True)
        total = sum(e.get('count', 0) for e in entries)
        unique_days = len(set(e.get('date') for e in entries))
        avg_per_day = total // unique_days if unique_days > 0 else 0
        
        # Находим первую и последнюю дату
        dates = sorted([e.get('date') for e in entries])
        first_date = datetime.strptime(dates[0], '%Y-%m-%d').strftime('%d.%m.%Y')
        last_date = datetime.strptime(dates[-1], '%Y-%m-%d').strftime('%d.%m.%Y')
        
        text += (
            f'✨ <b>Всего крестиков:</b> {format_number(total)}\n'
            f'📝 <b>Записей:</b> {len(entries)}\n'
            f'📅 <b>Дней с записями:</b> {unique_days}\n'
            f'📈 <b>Среднее в день:</b> {format_number(avg_per_day)}\n'
            f'📆 <b>Период:</b> {first_date} - {last_date}\n\n'
        )
    
    if projects:
        text += f'📸 <b>Работ с фото:</b> {len(projects)}\n\n'
    
    # Показываем фото работ с этим хэштегом
    if projects:
        # Отправляем первое фото с описанием
        first_project = projects[0]
        if first_project.get('imageFileId'):
            photo_caption = text
            if entries:
                photo_caption += '<b>Последние записи:</b>\n'
                for entry in entries[:5]:
                    date_str = datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                    photo_caption += f"📆 {date_str}: {format_number(entry['count'])} крестиков\n"
                if len(entries) > 5:
                    photo_caption += f"\n... и еще {len(entries) - 5} записей"
            
            await message.answer_photo(
                first_project['imageFileId'],
                caption=photo_caption,
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            
            # Отправляем остальные фото, если есть
            for project in projects[1:]:
                if project.get('imageFileId'):
                    await message.answer_photo(
                        project['imageFileId'],
                        caption=f'📸 <b>{project["name"]}</b>',
                        parse_mode='HTML'
                    )
        else:
            # Если нет фото, отправляем только текст
            if entries:
                text += '<b>Последние записи:</b>\n'
                for entry in entries[:10]:
                    date_str = datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                    text += f"📆 {date_str}: {format_number(entry['count'])} крестиков\n"
                if len(entries) > 10:
                    text += f"\n... и еще {len(entries) - 10} записей"
            
            await message.answer(
                text,
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
    else:
        # Если нет проектов, показываем только статистику
        if entries:
            text += '<b>Последние записи:</b>\n'
            for entry in entries[:10]:
                date_str = datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                text += f"📆 {date_str}: {entry['count']:,} крестиков\n"
            if len(entries) > 10:
                text += f"\n... и еще {len(entries) - 10} записей"
        
        await message.answer(
            text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data == "hashtags_menu")
async def callback_hashtags_menu(callback: CallbackQuery):
    await callback.answer()
    await show_hashtags_menu(callback.message, callback.from_user.id)

@router.callback_query(F.data.startswith("hashtag_"))
async def callback_hashtag(callback: CallbackQuery):
    await callback.answer()
    hashtag = callback.data.replace("hashtag_", "")
    await show_hashtag_progress(callback.message, callback.from_user.id, hashtag)

