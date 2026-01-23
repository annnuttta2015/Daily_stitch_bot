from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from dateutil import parser
from data.storage import add_count_to_date, get_entries, get_all_hashtags, get_user_challenges, update_user_challenge, format_number
from data.challenges import check_challenge_progress
from handlers.keyboards import get_back_keyboard
from utils import safe_answer_callback
import logging

router = Router()
logger = logging.getLogger(__name__)

# Состояния диалогов
pending_entries = {}

async def add_stitches_dialog(message: Message, user_id: int):
    logger.info(f"[ENTRIES] add_stitches_dialog вызван для user_id={user_id}")
    hashtag_hint = ""
    try:
        hashtags = get_all_hashtags(user_id)
        if hashtags:
            hashtag_hint = f"\n\n💡 Ваши хэштеги: {', '.join(hashtags[:5])}"
            if len(hashtags) > 5:
                hashtag_hint += "..."
    except Exception as e:
        logger.error(f"[ENTRIES] Ошибка при получении хэштегов в add_stitches_dialog: {e}", exc_info=True)
    
    # Клавиатура с кнопками "Сегодня" и "Вчера"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='📅 Сегодня', callback_data='entry_date_today'),
        InlineKeyboardButton(text='📅 Вчера', callback_data='entry_date_yesterday')
    ]])
    
    logger.info(f"[ENTRIES] Отправка сообщения с запросом даты")
    await message.answer(
        '📝 <b>Добавление крестиков</b>\n\n'
        'Введите дату в формате ДД.ММ.ГГГГ или нажмите кнопку:'
        + hashtag_hint,
        parse_mode='HTML',
        reply_markup=keyboard
    )
    pending_entries[user_id] = {'step': 'date'}
    logger.info(f"[ENTRIES] pending_entries обновлен для user_id={user_id}, step=date, keys: {list(pending_entries.keys())}")

async def process_entry_message(message: Message, user_id: int):
    logger.info(f"[ENTRIES] process_entry_message вызван для user_id={user_id}, pending_entries keys: {list(pending_entries.keys())}")
    if user_id not in pending_entries:
        logger.info(f"[ENTRIES] user_id {user_id} не найден в pending_entries")
        return False
    
    state = pending_entries[user_id]
    logger.info(f"[ENTRIES] Обработка сообщения для user_id={user_id}, step={state.get('step')}, text='{message.text[:50] if message.text else 'None'}'")
    
    if state['step'] == 'date':
        logger.info(f"[ENTRIES] Обработка даты для user_id={user_id}, text='{message.text}'")
        text = message.text.strip().lower() if message.text else ''
        
        date_obj = None
        date = None
        
        try:
            if text == 'сегодня' or text == 'today':
                date_obj = datetime.now()
                date = date_obj.strftime('%Y-%m-%d')
                logger.info(f"[ENTRIES] Установлена дата 'сегодня': {date}")
            elif text == 'вчера' or text == 'yesterday':
                date_obj = datetime.now() - timedelta(days=1)
                date = date_obj.strftime('%Y-%m-%d')
                logger.info(f"[ENTRIES] Установлена дата 'вчера': {date}")
            else:
                try:
                    # Пробуем распарсить дату
                    date_obj = parser.parse(message.text, dayfirst=True)
                    
                    # Валидация: проверяем, что год находится в разумных пределах
                    current_year = datetime.now().year
                    if date_obj.year < 1900 or date_obj.year > current_year + 1:
                        logger.warning(f"[ENTRIES] Некорректный год в дате: {date_obj.year}, text='{message.text}'")
                        await message.answer(
                            f'❌ Некорректная дата. Год должен быть от 1900 до {current_year + 1}.\n\n'
                            'Используйте ДД.ММ.ГГГГ или нажмите кнопку "📅 Сегодня"',
                            reply_markup=get_back_keyboard()
                        )
                        return True
                    
                    date = date_obj.strftime('%Y-%m-%d')
                    logger.info(f"[ENTRIES] Распарсена дата: {date}")
                except Exception as e:
                    logger.warning(f"[ENTRIES] Ошибка парсинга даты: {e}, text='{message.text}'", exc_info=True)
                    try:
                        await message.answer(
                            '❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или нажмите кнопку "📅 Сегодня"', 
                            reply_markup=get_back_keyboard()
                        )
                    except Exception as send_error:
                        logger.error(f"[ENTRIES] Ошибка при отправке сообщения об ошибке: {send_error}", exc_info=True)
                    return True
            
            # Проверяем, что date и date_obj установлены
            if not date or not date_obj:
                logger.error(f"[ENTRIES] date или date_obj не установлены после обработки: date={date}, date_obj={date_obj}")
                try:
                    await message.answer('❌ Ошибка при обработке даты. Попробуйте еще раз.', reply_markup=get_back_keyboard())
                except:
                    pass
                return True
            
            state['date'] = date
            state['step'] = 'count'
            logger.info(f"[ENTRIES] Установлен шаг 'count', date={date}")
            
            # Используем безопасное форматирование даты без locale
            try:
                months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                             'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
                if date_obj and hasattr(date_obj, 'day') and hasattr(date_obj, 'month') and hasattr(date_obj, 'year'):
                    date_formatted = f"{date_obj.day} {months_ru[date_obj.month - 1]} {date_obj.year}"
                else:
                    raise AttributeError("date_obj не имеет необходимых атрибутов")
            except (IndexError, AttributeError, TypeError) as e:
                logger.error(f"[ENTRIES] Ошибка при форматировании даты: {e}, date_obj={date_obj}")
                # Если ошибка форматирования, используем простой формат
                date_formatted = date.replace('-', '.')
            
            logger.info(f"[ENTRIES] Отправка сообщения с подтверждением даты: {date_formatted}")
            try:
                await message.answer(
                    f'✅ Дата: {date_formatted}\n\n'
                    'Введите количество крестиков (можно с половинкой, например: 254.5):',
                    reply_markup=get_back_keyboard()
                )
                logger.info(f"[ENTRIES] Сообщение с датой успешно отправлено")
            except Exception as e:
                logger.error(f"[ENTRIES] Ошибка при отправке сообщения с датой: {e}", exc_info=True)
                # Пробуем отправить без форматирования
                try:
                    await message.answer(
                        f'✅ Дата: {date}\n\n'
                        'Введите количество крестиков (можно с половинкой, например: 254.5):',
                        reply_markup=get_back_keyboard()
                    )
                    logger.info(f"[ENTRIES] Сообщение с датой отправлено в упрощенном формате")
                except Exception as e2:
                    logger.error(f"[ENTRIES] Критическая ошибка при отправке сообщения: {e2}", exc_info=True)
                    # Последняя попытка - без клавиатуры
                    try:
                        await message.answer(
                            f'✅ Дата: {date}\n\n'
                            'Введите количество крестиков (можно с половинкой, например: 254.5):'
                        )
                    except Exception as e3:
                        logger.error(f"[ENTRIES] Полный провал отправки сообщения: {e3}", exc_info=True)
            return True
        except Exception as e:
            logger.error(f"[ENTRIES] Критическая ошибка при обработке даты: {e}", exc_info=True)
            try:
                await message.answer(
                    '❌ Произошла ошибка при обработке даты. Попробуйте еще раз или используйте /start для перезапуска.',
                    reply_markup=get_back_keyboard()
                )
            except Exception as send_error:
                logger.error(f"[ENTRIES] Ошибка при отправке сообщения об ошибке: {send_error}", exc_info=True)
            return True
    
    elif state['step'] == 'count':
        logger.info(f"[ENTRIES] Обработка количества крестиков для user_id={user_id}, text='{message.text}'")
        try:
            # Поддержка дробных чисел (например, 254.5 для половины крестика)
            count_text = message.text.strip().replace(',', '.')  # Поддержка запятой и точки
            count = float(count_text)
            logger.info(f"[ENTRIES] Распарсено число: {count}")
            if count <= 0:
                logger.warning(f"[ENTRIES] Отрицательное или нулевое число: {count}")
                await message.answer('❌ Введите положительное число (можно с половинкой, например: 254.5)')
                return True
            
            state['count'] = count
            state['step'] = 'hashtag'
            logger.info(f"[ENTRIES] Установлен шаг 'hashtag', count={count}")
            
            try:
                logger.info("[ENTRIES] Получение хэштегов...")
                hashtags = get_all_hashtags(user_id)
                logger.info(f"[ENTRIES] Получено хэштегов: {len(hashtags) if hashtags else 0}")
                hashtag_hint = "\n\n💡 Отправьте хэштег (например: #работа1) или нажмите 'Пропустить'"
                if hashtags:
                    hashtag_hint += f"\nВаши хэштеги: {', '.join(hashtags[:5])}"
            except Exception as e:
                logger.error(f"[ENTRIES] Ошибка при получении хэштегов: {e}", exc_info=True)
                hashtag_hint = "\n\n💡 Отправьте хэштег (например: #работа1) или нажмите 'Пропустить'"
            
            # Клавиатура с кнопкой "Пропустить"
            logger.info("[ENTRIES] Создание клавиатуры...")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text='⏭️ Пропустить', callback_data='entry_hashtag_skip')
            ]])
            
            try:
                logger.info("[ENTRIES] Форматирование числа...")
                formatted_count = format_number(count)
                logger.info(f"[ENTRIES] Отформатированное число: {formatted_count}")
                response_text = f'✅ Количество: {formatted_count} крестиков' + hashtag_hint
                logger.info(f"[ENTRIES] Отправка сообщения с клавиатурой, длина текста: {len(response_text)}")
                await message.answer(
                    response_text,
                    reply_markup=keyboard
                )
                logger.info("[ENTRIES] Сообщение успешно отправлено")
            except Exception as e:
                # Если не удалось отправить с клавиатурой, пробуем без неё
                logger.error(f"[ENTRIES] Ошибка при отправке сообщения с клавиатурой: {e}", exc_info=True)
                try:
                    formatted_count = format_number(count)
                    logger.info("[ENTRIES] Попытка отправить сообщение без клавиатуры...")
                    await message.answer(
                        f'✅ Количество: {formatted_count} крестиков' + hashtag_hint
                    )
                    logger.info("[ENTRIES] Сообщение без клавиатуры успешно отправлено")
                except Exception as e2:
                    logger.error(f"[ENTRIES] Ошибка при отправке сообщения без клавиатуры: {e2}", exc_info=True)
                    await message.answer('✅ Количество крестиков сохранено. Введите хэштег или нажмите "Пропустить".')
            logger.info("[ENTRIES] Обработка количества крестиков завершена успешно")
            return True
        except ValueError as e:
            logger.warning(f"[ENTRIES] ValueError при парсинге числа: {e}, text='{message.text}'")
            await message.answer('❌ Введите число')
            return True
        except Exception as e:
            logger.error(f"[ENTRIES] Критическая ошибка при обработке количества крестиков: {e}", exc_info=True)
            await message.answer('❌ Произошла ошибка. Попробуйте еще раз.')
            return True
    
    elif state['step'] == 'hashtag':
        text = message.text.strip().lower()
        hashtag = None
        
        if text != 'пропустить' and text != 'skip' and text:
            # Извлекаем хэштег (убираем # если есть)
            hashtag = text.lstrip('#').strip()
            if not hashtag:
                await message.answer('❌ Хэштег не может быть пустым. Нажмите "Пропустить" если не нужен.', reply_markup=get_back_keyboard())
                return True
        
        # Сохраняем запись (с хэштегом или без)
        add_count_to_date(state['date'], state['count'], user_id, hashtag)
        
        # Используем безопасное форматирование даты
        try:
            entry_date = datetime.strptime(state['date'], '%Y-%m-%d')
            months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                         'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            date_str = f"{entry_date.day} {months_ru[entry_date.month - 1]} {entry_date.year}"
        except (ValueError, TypeError):
            # Если дата некорректная, показываем её как есть
            date_str = state['date'].replace('-', '.')
        
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

@router.callback_query(F.data == "entry_date_today")
async def callback_entry_date_today(callback: CallbackQuery):
    """Обработка кнопки 'Сегодня' при вводе даты"""
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    
    logger.info(f"[ENTRIES] Обработка кнопки 'Сегодня' для user_id={user_id}")
    
    if user_id not in pending_entries:
        logger.warning(f"[ENTRIES] user_id {user_id} не найден в pending_entries при обработке кнопки 'Сегодня'")
        await callback.message.answer('❌ Сессия истекла. Начните заново.')
        return
    
    state = pending_entries[user_id]
    if state.get('step') != 'date':
        logger.warning(f"[ENTRIES] Неверный шаг при обработке кнопки 'Сегодня': {state.get('step')}")
        await callback.message.answer('❌ Неверный шаг диалога.')
        return
    
    # Устанавливаем сегодняшнюю дату
    date = datetime.now().strftime('%Y-%m-%d')
    date_obj = datetime.now()
    state['date'] = date
    state['step'] = 'count'
    logger.info(f"[ENTRIES] Установлена дата 'сегодня': {date}, шаг изменен на 'count'")
    
    # Используем безопасное форматирование даты без locale
    months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    date_formatted = f"{date_obj.day} {months_ru[date_obj.month - 1]} {date_obj.year}"
    
    try:
        logger.info(f"[ENTRIES] Попытка отредактировать сообщение с датой")
        await callback.message.edit_text(
            f'✅ Дата: {date_formatted}\n\n'
            'Введите количество крестиков:',
            reply_markup=get_back_keyboard()
        )
        logger.info(f"[ENTRIES] Сообщение успешно отредактировано")
    except Exception as e:
        # Если не удалось отредактировать, отправляем новое сообщение
        logger.error(f"[ENTRIES] Ошибка при редактировании сообщения: {e}", exc_info=True)
        try:
            await callback.message.answer(
                f'✅ Дата: {date_formatted}\n\n'
                'Введите количество крестиков:',
                reply_markup=get_back_keyboard()
            )
            logger.info(f"[ENTRIES] Новое сообщение с датой отправлено")
        except Exception as e2:
            logger.error(f"[ENTRIES] Критическая ошибка при отправке сообщения: {e2}", exc_info=True)

@router.callback_query(F.data == "entry_date_yesterday")
async def callback_entry_date_yesterday(callback: CallbackQuery):
    """Обработка кнопки 'Вчера' при вводе даты"""
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    
    logger.info(f"[ENTRIES] Обработка кнопки 'Вчера' для user_id={user_id}")
    
    if user_id not in pending_entries:
        logger.warning(f"[ENTRIES] user_id {user_id} не найден в pending_entries при обработке кнопки 'Вчера'")
        await callback.message.answer('❌ Сессия истекла. Начните заново.')
        return
    
    state = pending_entries[user_id]
    if state.get('step') != 'date':
        logger.warning(f"[ENTRIES] Неверный шаг при обработке кнопки 'Вчера': {state.get('step')}")
        await callback.message.answer('❌ Неверный шаг диалога.')
        return
    
    # Устанавливаем вчерашнюю дату
    date_obj = datetime.now() - timedelta(days=1)
    date = date_obj.strftime('%Y-%m-%d')
    state['date'] = date
    state['step'] = 'count'
    logger.info(f"[ENTRIES] Установлена дата 'вчера': {date}, шаг изменен на 'count'")
    
    # Используем безопасное форматирование даты без locale
    months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    date_formatted = f"{date_obj.day} {months_ru[date_obj.month - 1]} {date_obj.year}"
    
    try:
        logger.info(f"[ENTRIES] Попытка отредактировать сообщение с датой")
        await callback.message.edit_text(
            f'✅ Дата: {date_formatted}\n\n'
            'Введите количество крестиков:',
            reply_markup=get_back_keyboard()
        )
        logger.info(f"[ENTRIES] Сообщение успешно отредактировано")
    except Exception as e:
        # Если не удалось отредактировать, отправляем новое сообщение
        logger.error(f"[ENTRIES] Ошибка при редактировании сообщения: {e}", exc_info=True)
        try:
            await callback.message.answer(
                f'✅ Дата: {date_formatted}\n\n'
                'Введите количество крестиков:',
                reply_markup=get_back_keyboard()
            )
            logger.info(f"[ENTRIES] Новое сообщение с датой отправлено")
        except Exception as e2:
            logger.error(f"[ENTRIES] Критическая ошибка при отправке сообщения: {e2}", exc_info=True)

@router.callback_query(F.data == "entry_hashtag_skip")
async def callback_entry_hashtag_skip(callback: CallbackQuery):
    """Обработка кнопки 'Пропустить' при вводе хэштега"""
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    
    logger.info(f"[ENTRIES] Обработка кнопки 'Пропустить' для user_id={user_id}")
    
    if user_id not in pending_entries:
        logger.warning(f"[ENTRIES] user_id {user_id} не найден в pending_entries при обработке кнопки 'Пропустить'")
        await callback.message.answer('❌ Сессия истекла. Начните заново.')
        return
    
    state = pending_entries[user_id]
    if state.get('step') != 'hashtag':
        logger.warning(f"[ENTRIES] Неверный шаг при обработке кнопки 'Пропустить': {state.get('step')}")
        await callback.message.answer('❌ Неверный шаг диалога.')
        return
    
    # Сохраняем запись без хэштега
    logger.info(f"[ENTRIES] Сохранение записи без хэштега: date={state.get('date')}, count={state.get('count')}")
    add_count_to_date(state['date'], state['count'], user_id, None)
    
    # Используем безопасное форматирование даты
    try:
        entry_date = datetime.strptime(state['date'], '%Y-%m-%d')
        months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                     'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        date_str = f"{entry_date.day} {months_ru[entry_date.month - 1]} {entry_date.year}"
    except (ValueError, TypeError):
        # Если дата некорректная, показываем её как есть
        date_str = state['date'].replace('-', '.')
    
    result_text = (
        f'✅ <b>Добавлено!</b>\n\n'
        f'Дата: {date_str}\n'
        f'Крестиков: {format_number(state["count"])}'
    )
    
    try:
        logger.info(f"[ENTRIES] Попытка отредактировать сообщение после пропуска хэштега")
        await callback.message.edit_text(
            result_text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        logger.info(f"[ENTRIES] Сообщение успешно отредактировано")
    except Exception as e:
        logger.error(f"[ENTRIES] Ошибка при редактировании сообщения: {e}", exc_info=True)
        try:
            await callback.message.answer(
                result_text,
                parse_mode='HTML',
                reply_markup=get_back_keyboard()
            )
            logger.info(f"[ENTRIES] Новое сообщение отправлено")
        except Exception as e2:
            logger.error(f"[ENTRIES] Критическая ошибка при отправке сообщения: {e2}", exc_info=True)
    
    # Проверяем челленджи после добавления крестиков
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        await check_challenges_on_entry(user_id, bot)
    finally:
        await bot.session.close()
    
    del pending_entries[user_id]
    logger.info(f"[ENTRIES] Диалог завершен, pending_entries очищен для user_id={user_id}")

