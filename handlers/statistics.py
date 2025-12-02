from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from collections import defaultdict
from data.storage import get_entries, format_number
from handlers.keyboards import get_back_keyboard
from utils import safe_answer_callback
import logging

router = Router()
logger = logging.getLogger(__name__)

async def show_statistics(message: Message, user_id: int):
    try:
        entries = get_entries(user_id)
        logger.debug(f"[STATISTICS] Получено {len(entries)} записей для user_id={user_id}")
        
        # Фильтруем только валидные записи с датой
        valid_entries = []
        for entry in entries:
            if not entry.get('date'):
                logger.warning(f"[STATISTICS] Пропущена запись без даты для user_id={user_id}: {entry}")
                continue
            try:
                # Проверяем, что дата в правильном формате
                datetime.strptime(entry['date'], '%Y-%m-%d')
                valid_entries.append(entry)
            except (ValueError, TypeError) as e:
                logger.warning(f"[STATISTICS] Пропущена запись с некорректной датой для user_id={user_id}: дата='{entry.get('date')}', ошибка: {e}")
                continue
        
        entries = valid_entries
        logger.debug(f"[STATISTICS] После фильтрации осталось {len(entries)} валидных записей для user_id={user_id}")
        
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        
        # Первый день месяца
        month_start = datetime(today.year, today.month, 1).date()
        month_start_str = month_start.strftime('%Y-%m-%d')
        
        # Первый день года
        year_start = datetime(today.year, 1, 1).date()
        year_start_str = year_start.strftime('%Y-%m-%d')
        
        today_count = sum(e.get('count', 0) for e in entries if e.get('date') == today_str)
        month_count = sum(e.get('count', 0) for e in entries if e.get('date') >= month_start_str)
        year_count = sum(e.get('count', 0) for e in entries if e.get('date') >= year_start_str)
        total_count = sum(e.get('count', 0) for e in entries)
        
        unique_days = len(set(e.get('date') for e in entries))
        average_per_day = total_count // unique_days if unique_days > 0 else 0
        
        # Детальная статистика
        # Лучший день (максимум крестиков)
        best_day = None
        best_day_count = 0
        best_day_date = None
        
        # Лучший месяц
        month_stats = defaultdict(float)
        for entry in entries:
            try:
                entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
                month_key = f"{entry_date.year}-{entry_date.month:02d}"
                month_stats[month_key] += float(entry.get('count', 0))
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"[STATISTICS] Ошибка при обработке записи для лучшего месяца: дата='{entry.get('date')}', ошибка: {e}")
                continue
        
        best_month = None
        best_month_count = 0
        if month_stats:
            best_month = max(month_stats.items(), key=lambda x: x[1])
            best_month_count = best_month[1]
            best_month = best_month[0]
        
        # Самый продуктивный день недели
        weekday_stats = defaultdict(float)
        weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        
        for entry in entries:
            try:
                entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
                weekday = entry_date.weekday()  # 0 = понедельник
                weekday_stats[weekday] += float(entry.get('count', 0))
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"[STATISTICS] Ошибка при обработке записи для дня недели: дата='{entry.get('date')}', ошибка: {e}")
                continue
        
        best_weekday = None
        best_weekday_count = 0
        if weekday_stats:
            best_weekday = max(weekday_stats.items(), key=lambda x: x[1])
            best_weekday_count = best_weekday[1]
            best_weekday = weekday_names[best_weekday[0]]
        
        # Рекорды
        for entry in entries:
            try:
                count = float(entry.get('count', 0))
                if count > best_day_count:
                    best_day_count = count
                    best_day_date = entry['date']
            except (ValueError, TypeError) as e:
                logger.warning(f"[STATISTICS] Ошибка при обработке записи для рекордов: {entry}, ошибка: {e}")
                continue
        
        if best_day_date:
            try:
                best_day = datetime.strptime(best_day_date, '%Y-%m-%d').strftime('%d.%m.%Y')
            except (ValueError, TypeError) as e:
                logger.warning(f"[STATISTICS] Ошибка при форматировании лучшего дня: {best_day_date}, ошибка: {e}")
                best_day = None
        
        text = (
            '<b>📊 Статистика</b>\n\n'
            f'📅 <b>Сегодня:</b> {format_number(today_count)} крестиков\n'
            f'📆 <b>Этот месяц:</b> {format_number(month_count)} крестиков\n'
            f'📆 <b>Этот год:</b> {format_number(year_count)} крестиков\n'
            f'✨ <b>Всего:</b> {format_number(total_count)} крестиков\n'
            f'📈 <b>Среднее в день:</b> {format_number(average_per_day)} крестиков\n'
            f'📝 <b>Дней с записями:</b> {unique_days}\n\n'
        )
        
        # Детальная статистика
        text += '<b>🏆 Рекорды:</b>\n'
        if best_day:
            text += f'🥇 Лучший день: {format_number(best_day_count)} крестиков ({best_day})\n'
        else:
            text += '🥇 Лучший день: нет данных\n'
        
        if best_month:
            try:
                year, month = best_month.split('-')
                month_name = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                             'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'][int(month) - 1]
                text += f'📅 Лучший месяц: {format_number(best_month_count)} крестиков ({month_name} {year})\n'
            except (ValueError, IndexError) as e:
                logger.warning(f"[STATISTICS] Ошибка при форматировании лучшего месяца: {best_month}, ошибка: {e}")
                text += '📅 Лучший месяц: нет данных\n'
        else:
            text += '📅 Лучший месяц: нет данных\n'
        
        if best_weekday:
            text += f'📆 Самый продуктивный день недели: {best_weekday} ({format_number(best_weekday_count)} крестиков)\n'
        else:
            text += '📆 Самый продуктивный день недели: нет данных\n'
        
        keyboard = [
            [InlineKeyboardButton(text='📊 Сравнение периодов', callback_data='period_comparison')],
            [InlineKeyboardButton(text='📥 Экспорт данных', callback_data='export_data')],
            [InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')]
        ]
        
        try:
            await message.answer(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            logger.info(f"[STATISTICS] Сообщение со статистикой отправлено для user_id={user_id}")
        except Exception as e:
            logger.error(f"[STATISTICS] Ошибка при отправке сообщения для user_id={user_id}: {e}", exc_info=True)
            # Если не удалось отправить, пробуем еще раз через то же сообщение
            try:
                await message.answer(
                    text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
            except Exception as e2:
                logger.error(f"[STATISTICS] Критическая ошибка при отправке статистики для user_id={user_id}: {e2}", exc_info=True)
                raise
                
    except Exception as e:
        logger.error(f"[STATISTICS] Критическая ошибка в show_statistics для user_id={user_id}: {e}", exc_info=True)
        
        error_text = (
            '❌ <b>Ошибка при загрузке статистики</b>\n\n'
            'Попробуйте позже или используйте команду /stats'
        )
        keyboard = [
            [InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')]
        ]
        
        try:
            if message:
                await message.answer(
                    error_text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
        except:
            pass
        raise

@router.callback_query(F.data == "statistics")
async def callback_statistics(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"[STATISTICS] Обработка callback_statistics для user_id={user_id}")
    
    try:
        await safe_answer_callback(callback)
    except Exception as e:
        logger.error(f"[STATISTICS] Ошибка при safe_answer_callback для user_id={user_id}: {e}", exc_info=True)
    
    # Проверяем, что сообщение доступно
    if not callback.message:
        logger.error(f"[STATISTICS] callback.message is None для user_id={user_id}")
        try:
            # Используем bot из callback
            await callback.bot.send_message(user_id, "❌ Ошибка: сообщение недоступно. Попробуйте вызвать /start")
        except Exception as e:
            logger.error(f"[STATISTICS] Не удалось отправить сообщение об ошибке для user_id={user_id}: {e}")
        return
    
    try:
        await show_statistics(callback.message, user_id)
        logger.info(f"[STATISTICS] Статистика успешно показана для user_id={user_id}")
    except Exception as e:
        logger.error(f"[STATISTICS] Ошибка при показе статистики для user_id={user_id}: {e}", exc_info=True)
        
        # Пытаемся отправить сообщение об ошибке
        try:
            error_text = (
                '❌ <b>Ошибка при загрузке статистики</b>\n\n'
                'Попробуйте позже или используйте команду /stats'
            )
            keyboard = [
                [InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')]
            ]
            
            if callback.message:
                await callback.message.answer(
                    error_text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
        except Exception as e2:
            logger.error(f"[STATISTICS] Не удалось отправить сообщение об ошибке для user_id={user_id}: {e2}")
