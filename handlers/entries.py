from aiogram.types import Message
from datetime import datetime
from dateutil import parser
from data.storage import add_count_to_date, get_entries, get_all_hashtags, get_user_challenges, update_user_challenge, format_number
from data.challenges import check_challenge_progress
from handlers.keyboards import get_back_keyboard

# Состояния диалогов
pending_entries = {}

async def add_stitches_dialog(message: Message, user_id: int):
    hashtags = get_all_hashtags(user_id)
    hashtag_hint = ""
    if hashtags:
        hashtag_hint = f"\n\n💡 Ваши хэштеги: {', '.join(hashtags[:5])}"
        if len(hashtags) > 5:
            hashtag_hint += "..."
    
    await message.answer(
        '📝 <b>Добавление крестиков</b>\n\n'
        'Введите дату в формате ДД.ММ.ГГГГ (или отправьте "сегодня"):'
        + hashtag_hint,
        parse_mode='HTML'
    )
    pending_entries[user_id] = {'step': 'date'}

async def process_entry_message(message: Message, user_id: int):
    if user_id not in pending_entries:
        return False
    
    state = pending_entries[user_id]
    
    if state['step'] == 'date':
        text = message.text.strip().lower()
        
        if text == 'сегодня' or text == 'today':
            date = datetime.now().strftime('%Y-%m-%d')
            date_obj = datetime.now()
        else:
            try:
                # Пробуем распарсить дату
                date_obj = parser.parse(message.text, dayfirst=True)
                date = date_obj.strftime('%Y-%m-%d')
            except:
                await message.answer('❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или "сегодня"')
                return True
        
        state['date'] = date
        state['step'] = 'count'
        # Используем безопасное форматирование даты без locale
        months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                     'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        date_formatted = f"{date_obj.day} {months_ru[date_obj.month - 1]} {date_obj.year}"
        await message.answer(
            f'✅ Дата: {date_formatted}\n\n'
            'Введите количество крестиков:',
            reply_markup=get_back_keyboard()
        )
        return True
    
    elif state['step'] == 'count':
        try:
            count = int(message.text)
            if count <= 0:
                await message.answer('❌ Введите положительное число')
                return True
            
            state['count'] = count
            state['step'] = 'hashtag'
            
            hashtags = get_all_hashtags(user_id)
            hashtag_hint = "\n\n💡 Отправьте хэштег (например: #работа1) или 'пропустить'"
            if hashtags:
                hashtag_hint += f"\nВаши хэштеги: {', '.join(hashtags[:5])}"
            
            await message.answer(
                f'✅ Количество: {format_number(count)} крестиков'
                + hashtag_hint,
                reply_markup=get_back_keyboard()
            )
            return True
        except ValueError:
            await message.answer('❌ Введите число')
            return True
    
    elif state['step'] == 'hashtag':
        text = message.text.strip().lower()
        hashtag = None
        
        if text != 'пропустить' and text != 'skip' and text:
            # Извлекаем хэштег (убираем # если есть)
            hashtag = text.lstrip('#').strip()
            if not hashtag:
                await message.answer('❌ Хэштег не может быть пустым. Отправьте "пропустить" если не нужен.')
                return True
        
            add_count_to_date(state['date'], state['count'], user_id, hashtag)
            # Используем безопасное форматирование даты
            entry_date = datetime.strptime(state['date'], '%Y-%m-%d')
            months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                         'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            date_str = f"{entry_date.day} {months_ru[entry_date.month - 1]} {entry_date.year}"
            
            result_text = (
                f'✅ <b>Добавлено!</b>\n\n'
                f'Дата: {date_str}\n'
                f'Крестиков: {format_number(state["count"])}'
            )
            if hashtag:
                result_text += f'\nХэштег: #{hashtag}'
        
        await message.answer(
            result_text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        
        # Проверяем челленджи после добавления крестиков
        # Используем бот из контекста, если доступен
        from aiogram import Bot
        from config import BOT_TOKEN
        bot = Bot(token=BOT_TOKEN)
        try:
            await check_challenges_on_entry(user_id, bot)
        finally:
            await bot.session.close()
        
        del pending_entries[user_id]
        return True
    
    return False

async def show_history(message: Message, user_id: int):
    entries = get_entries(user_id)
    entries.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    if not entries:
        await message.answer('📝 Пока нет записей.', reply_markup=get_back_keyboard())
        return
    
    from datetime import datetime
    
    # Используем безопасное форматирование без locale
    months_short = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн',
                    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
    
    total_entries = len(entries)
    text = f'<b>📅 История записей (всего: {total_entries}):</b>\n\n'
    
    # Если записей много, показываем все, но предупреждаем
    for entry in entries:
        entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
        date_str = f"{entry_date.day} {months_short[entry_date.month - 1]} {entry_date.year}"
        hashtag_info = ""
        if entry.get('hashtag'):
            hashtag_info = f" #{entry.get('hashtag')}"
        text += f"📆 {date_str}: {format_number(entry['count'])} крестиков{hashtag_info}\n"
    
    # Telegram ограничивает длину сообщения до 4096 символов
    # Если текст слишком длинный, разбиваем на несколько сообщений
    max_length = 4000
    if len(text) > max_length:
        # Отправляем первую часть
        first_part = text[:max_length]
        last_newline = first_part.rfind('\n')
        if last_newline > 0:
            first_part = text[:last_newline]
            remaining = text[last_newline+1:]
        else:
            remaining = text[max_length:]
        
        await message.answer(first_part, parse_mode='HTML', reply_markup=get_back_keyboard())
        
        # Отправляем оставшиеся части
        while remaining:
            if len(remaining) > max_length:
                last_newline = remaining[:max_length].rfind('\n')
                if last_newline > 0:
                    part = remaining[:last_newline]
                    remaining = remaining[last_newline+1:]
                else:
                    part = remaining[:max_length]
                    remaining = remaining[max_length:]
                await message.answer(part, parse_mode='HTML')
            else:
                await message.answer(remaining, parse_mode='HTML')
                break
    else:
        await message.answer(text, parse_mode='HTML', reply_markup=get_back_keyboard())

def clear_pending(user_id: int):
    if user_id in pending_entries:
        del pending_entries[user_id]

async def check_challenges_on_entry(user_id: int, bot_instance=None):
    """Проверить прогресс челленджей после добавления крестиков"""
    user_challenges = get_user_challenges(user_id)
    active_challenges = [c for c in user_challenges if not c.get('completed', False)]
    
    if not active_challenges:
        return
    
    completed_challenges = []
    
    for user_challenge in active_challenges:
        challenge_id = user_challenge.get('challengeId')
        progress_data = check_challenge_progress(user_id, challenge_id, user_challenge)
        
        if progress_data and progress_data.get('completed') and not user_challenge.get('completed'):
            # Челлендж выполнен!
            update_user_challenge(challenge_id, user_id, {'completed': True, 'completedAt': datetime.now().strftime('%Y-%m-%d')})
            completed_challenges.append(challenge_id)
    
    # Отправляем уведомления о выполненных челленджах
    if completed_challenges and bot_instance:
        from data.challenges import get_challenge_by_id
        for challenge_id in completed_challenges:
            challenge_data = get_challenge_by_id(challenge_id)
            if challenge_data:
                try:
                    await bot_instance.send_message(
                        user_id,
                        f'🎉 <b>Поздравляем!</b>\n\n'
                        f'Вы выполнили челлендж:\n'
                        f'{challenge_data["emoji"]} <b>{challenge_data["name"]}</b>\n\n'
                        f'Отличная работа! 🏆',
                        parse_mode='HTML'
                    )
                except:
                    pass  # Игнорируем ошибки отправки

