from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from data.storage import get_user_challenges, add_user_challenge, delete_user_challenge, get_user_challenge, format_number
from data.challenges import get_available_challenges, get_challenge_by_id, check_challenge_progress
from handlers.keyboards import get_back_keyboard

router = Router()

async def show_challenges_menu(message: Message, user_id: int):
    """Показать меню челленджей"""
    available = get_available_challenges()
    user_challenges = get_user_challenges(user_id)
    active_challenge_ids = {c.get('challengeId') for c in user_challenges if not c.get('completed', False)}
    
    text = '<b>🏆 Челленджи</b>\n\n'
    text += '<b>📋 Доступные челленджи:</b>\n\n'
    
    keyboard = []
    for i, challenge in enumerate(available, 1):
        is_active = challenge['id'] in active_challenge_ids
        status = '✅ Активен' if is_active else ''
        text += f"{i}. {challenge['emoji']} <b>{challenge['name']}</b>\n"
        text += f"   {challenge['description']} {status}\n\n"
        
        if not is_active:
            keyboard.append([InlineKeyboardButton(
                text=f"➕ {challenge['name']}",
                callback_data=f"challenge_select_{challenge['id']}"
            )])
    
    if user_challenges:
        text += '\n<b>📊 Ваши активные челленджи:</b>\n\n'
        active_challenges = [c for c in user_challenges if not c.get('completed', False)]
        
        if active_challenges:
            for challenge in active_challenges[:5]:  # Показываем до 5 активных
                challenge_data = get_challenge_by_id(challenge.get('challengeId', ''))
                if challenge_data:
                    progress_data = check_challenge_progress(user_id, challenge['challengeId'], challenge)
                    if progress_data:
                        progress_bar = "█" * int(progress_data['progress'] / 5) + "░" * (20 - int(progress_data['progress'] / 5))
                        
                        if progress_data['type'] == 'count':
                            text += f"{challenge_data['emoji']} <b>{challenge_data['name']}</b>\n"
                            text += f"   {format_number(progress_data['current'])} / {format_number(progress_data['target'])} ({progress_data['progress']:.1f}%)\n"
                            text += f"   Осталось дней: {progress_data['days_left']}\n"
                            text += f"   {progress_bar}\n\n"
                        elif progress_data['type'] == 'streak':
                            text += f"{challenge_data['emoji']} <b>{challenge_data['name']}</b>\n"
                            text += f"   {progress_data['current']} / {progress_data['target']} дней ({progress_data['progress']:.1f}%)\n"
                            text += f"   Осталось: {progress_data['days_left']} дней\n"
                            text += f"   {progress_bar}\n\n"
                        elif progress_data['type'] == 'daily_minimum':
                            text += f"{challenge_data['emoji']} <b>{challenge_data['name']}</b>\n"
                            text += f"   {progress_data['current']} / {progress_data['target']} дней ({progress_data['progress']:.1f}%)\n"
                            text += f"   Минимум: {progress_data['daily_target']} крестиков в день\n"
                            text += f"   Осталось дней: {progress_data['days_left']}\n"
                            text += f"   {progress_bar}\n\n"
                        
                        keyboard.append([InlineKeyboardButton(
                            text=f"📊 {challenge_data['name']}",
                            callback_data=f"challenge_view_{challenge['challengeId']}"
                        )])
        else:
            text += "Нет активных челленджей\n\n"
    
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def show_challenge_details(message: Message, user_id: int, challenge_id: str):
    """Показать детали челленджа"""
    challenge_data = get_challenge_by_id(challenge_id)
    if not challenge_data:
        await message.answer('❌ Челлендж не найден', reply_markup=get_back_keyboard())
        return
    
    user_challenge = get_user_challenge(challenge_id, user_id)
    
    if not user_challenge:
        # Показываем информацию о челлендже перед выбором
        text = (
            f"<b>{challenge_data['emoji']} {challenge_data['name']}</b>\n\n"
            f"{challenge_data['description']}\n\n"
            f"<b>Начать этот челлендж?</b>"
        )
        keyboard = [
            [InlineKeyboardButton(text='✅ Начать', callback_data=f"challenge_start_{challenge_id}")],
            [InlineKeyboardButton(text='🔙 Назад', callback_data='challenges_menu')]
        ]
    else:
        # Показываем прогресс
        progress_data = check_challenge_progress(user_id, challenge_id, user_challenge)
        if not progress_data:
            await message.answer('❌ Ошибка при проверке прогресса', reply_markup=get_back_keyboard())
            return
        
        progress_bar = "█" * int(progress_data['progress'] / 5) + "░" * (20 - int(progress_data['progress'] / 5))
        
        text = f"<b>{challenge_data['emoji']} {challenge_data['name']}</b>\n\n"
        text += f"{challenge_data['description']}\n\n"
        text += f"<b>Прогресс:</b>\n"
        
        if progress_data['type'] == 'count':
            text += f"   {format_number(progress_data['current'])} / {format_number(progress_data['target'])} крестиков\n"
            text += f"   {progress_data['progress']:.1f}% выполнено\n"
            text += f"   Осталось дней: {progress_data['days_left']}\n"
        elif progress_data['type'] == 'streak':
            text += f"   {progress_data['current']} / {progress_data['target']} дней подряд\n"
            text += f"   {progress_data['progress']:.1f}% выполнено\n"
            text += f"   Осталось: {progress_data['days_left']} дней\n"
        elif progress_data['type'] == 'daily_minimum':
            text += f"   {progress_data['current']} / {progress_data['target']} дней выполнено\n"
            text += f"   Минимум: {progress_data['daily_target']} крестиков в день\n"
            text += f"   {progress_data['progress']:.1f}% выполнено\n"
            text += f"   Осталось дней: {progress_data['days_left']}\n"
        
        text += f"\n{progress_bar}\n"
        
        if progress_data['completed']:
            text += "\n🎉 <b>Челлендж выполнен!</b>"
        
        keyboard = [
            [InlineKeyboardButton(text='🗑️ Отменить челлендж', callback_data=f"challenge_cancel_{challenge_id}")],
            [InlineKeyboardButton(text='🔙 Назад', callback_data='challenges_menu')]
        ]
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "challenges_menu")
async def callback_challenges_menu(callback: CallbackQuery):
    await callback.answer()
    await show_challenges_menu(callback.message, callback.from_user.id)

@router.callback_query(F.data.startswith("challenge_select_"))
async def callback_challenge_select(callback: CallbackQuery):
    await callback.answer()
    challenge_id = callback.data.replace("challenge_select_", "")
    await show_challenge_details(callback.message, callback.from_user.id, challenge_id)

@router.callback_query(F.data.startswith("challenge_start_"))
async def callback_challenge_start(callback: CallbackQuery):
    await callback.answer()
    challenge_id = callback.data.replace("challenge_start_", "")
    
    # Проверяем, не активен ли уже этот челлендж
    existing = get_user_challenge(challenge_id, callback.from_user.id)
    if existing and not existing.get('completed', False):
        await callback.message.answer(
            '⚠️ Этот челлендж уже активен!',
            reply_markup=get_back_keyboard()
        )
        return
    
    # Создаем новый челлендж
    challenge = {
        'id': f"user_challenge-{callback.from_user.id}-{int(datetime.now().timestamp())}",
        'challengeId': challenge_id,
        'userId': callback.from_user.id,
        'startDate': datetime.now().strftime('%Y-%m-%d'),
        'completed': False
    }
    
    add_user_challenge(challenge)
    
    challenge_data = get_challenge_by_id(challenge_id)
    await callback.message.answer(
        f'✅ <b>Челлендж начат!</b>\n\n'
        f'{challenge_data["emoji"]} <b>{challenge_data["name"]}</b>\n\n'
        f'Удачи! 🍀',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )
    await show_challenges_menu(callback.message, callback.from_user.id)

@router.callback_query(F.data.startswith("challenge_view_"))
async def callback_challenge_view(callback: CallbackQuery):
    await callback.answer()
    challenge_id = callback.data.replace("challenge_view_", "")
    await show_challenge_details(callback.message, callback.from_user.id, challenge_id)

@router.callback_query(F.data.startswith("challenge_cancel_"))
async def callback_challenge_cancel(callback: CallbackQuery):
    await callback.answer()
    challenge_id = callback.data.replace("challenge_cancel_", "")
    delete_user_challenge(challenge_id, callback.from_user.id)
    await callback.message.answer(
        '✅ Челлендж отменен',
        reply_markup=get_back_keyboard()
    )
    await show_challenges_menu(callback.message, callback.from_user.id)

