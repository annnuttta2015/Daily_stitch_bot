from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from dateutil import parser
from data.storage import get_plans, save_plan, delete_plan, get_entries, format_number
from handlers.keyboards import get_back_keyboard
from utils import safe_answer_callback

router = Router()

pending_plans = {}

async def show_plans(message: Message, user_id: int):
    """Показать список планов"""
    plans = get_plans(user_id)
    plans.sort(key=lambda x: x.get('targetDate', ''), reverse=False)
    
    if not plans:
        keyboard = [
            [InlineKeyboardButton(text='➕ Создать план', callback_data='plan_add')],
            [InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')]
        ]
        await message.answer(
            '📋 <b>Планы/Цели</b>\n\n'
            'У вас пока нет планов. Создайте первый план!',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
    
    text = '<b>📋 Ваши планы и цели:</b>\n\n'
    keyboard = []
    
    for i, plan in enumerate(plans[:20], 1):
        name = plan.get('name', 'Без названия')
        target = plan.get('targetCount', 0)
        target_date = plan.get('targetDate', '')
        
        # Считаем прогресс
        entries = get_entries(user_id)
        hashtag = plan.get('hashtag')
        if hashtag:
            plan_entries = [e for e in entries if e.get('hashtag') == hashtag]
        else:
            plan_entries = entries
        
        current = sum(e.get('count', 0) for e in plan_entries)
        progress = (current / target * 100) if target > 0 else 0
        progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
        
        status = "✅" if current >= target else "⏳"
        date_info = f" до {target_date}" if target_date else ""
        
        text += f"{i}. {status} <b>{name}</b>\n"
        text += f"   {format_number(current)} / {format_number(target)} крестиков ({progress:.1f}%)\n"
        text += f"   {progress_bar}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {name[:30]}",
            callback_data=f"plan_{plan.get('id')}"
        )])
    
    keyboard.append([InlineKeyboardButton(text='➕ Создать план', callback_data='plan_add')])
    keyboard.append([InlineKeyboardButton(text='🔙 Главное меню', callback_data='main_menu')])
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def add_plan_dialog(message: Message, user_id: int):
    """Начать диалог создания плана"""
    await message.answer(
        '📋 <b>Создание плана</b>\n\n'
        'Введите название плана:',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )
    pending_plans[user_id] = {'step': 'name'}

async def process_plan_message(message: Message, user_id: int):
    """Обработать сообщение для плана"""
    if user_id not in pending_plans:
        return False
    
    state = pending_plans[user_id]
    
    if state['step'] == 'name':
        name = message.text.strip()
        if not name:
            await message.answer('❌ Название не может быть пустым')
            return True
        
        state['name'] = name
        state['step'] = 'target'
        await message.answer(
            f'✅ Название: {name}\n\n'
            'Введите целевое количество крестиков:',
            reply_markup=get_back_keyboard()
        )
        return True
    
    elif state['step'] == 'target':
        try:
            target = int(message.text)
            if target <= 0:
                await message.answer('❌ Введите положительное число')
                return True
            
            state['target'] = target
            state['step'] = 'hashtag'
            await message.answer(
                f'✅ Цель: {format_number(target)} крестиков\n\n'
                'Введите хэштег для отслеживания (или "пропустить"):',
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
            hashtag = text.lstrip('#').strip()
        
        state['hashtag'] = hashtag
        state['step'] = 'date'
        date_hint = "\n\n💡 Введите дату цели (ДД.ММ.ГГГГ) или 'пропустить'"
        if hashtag:
            date_hint += f"\nХэштег: #{hashtag}"
        await message.answer(
            'Введите дату цели:' + date_hint,
            reply_markup=get_back_keyboard()
        )
        return True
    
    elif state['step'] == 'date':
        text = message.text.strip().lower()
        target_date = None
        
        if text != 'пропустить' and text != 'skip':
            try:
                date_obj = parser.parse(text, dayfirst=True)
                target_date = date_obj.strftime('%Y-%m-%d')
            except:
                await message.answer('❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или "пропустить"')
                return True
        
        plan = {
            'id': f"plan-{user_id}-{int(datetime.now().timestamp())}",
            'name': state['name'],
            'targetCount': state['target'],
            'hashtag': state.get('hashtag'),
            'targetDate': target_date,
            'userId': user_id,
            'createdAt': datetime.now().strftime('%Y-%m-%d')
        }
        
        save_plan(plan)
        
        result_text = (
            f'✅ <b>План создан!</b>\n\n'
            f'Название: {plan["name"]}\n'
            f'Цель: {format_number(plan["targetCount"])} крестиков'
        )
        if plan.get('hashtag'):
            result_text += f'\nХэштег: #{plan["hashtag"]}'
        if plan.get('targetDate'):
            result_text += f'\nДата цели: {target_date}'
        
        await message.answer(
            result_text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        del pending_plans[user_id]
        return True
    
    return False

async def show_plan(message: Message, user_id: int, plan_id: str):
    """Показать детали плана"""
    plans = get_plans(user_id)
    plan = next((p for p in plans if p.get('id') == plan_id), None)
    
    if not plan:
        await message.answer('❌ План не найден', reply_markup=get_back_keyboard())
        return
    
    # Считаем прогресс
    entries = get_entries(user_id)
    hashtag = plan.get('hashtag')
    if hashtag:
        plan_entries = [e for e in entries if e.get('hashtag') == hashtag]
    else:
        plan_entries = entries
    
    current = sum(e.get('count', 0) for e in plan_entries)
    target = plan.get('targetCount', 0)
    progress = (current / target * 100) if target > 0 else 0
    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
    remaining = max(0, target - current)
    
    text = (
        f'<b>📋 {plan.get("name")}</b>\n\n'
        f'Прогресс: {format_number(current)} / {format_number(target)} крестиков\n'
        f'{progress:.1f}% выполнено\n'
        f'{progress_bar}\n'
        f'Осталось: {format_number(remaining)} крестиков\n'
    )
    
    if plan.get('hashtag'):
        text += f'\nХэштег: #{plan.get("hashtag")}'
    if plan.get('targetDate'):
        text += f'\nЦелевая дата: {plan.get("targetDate")}'
    
    keyboard = [
        [InlineKeyboardButton(text='🗑️ Удалить', callback_data=f"plan_delete_{plan_id}")],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='plans_menu')]
    ]
    
    await message.answer(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "plans_menu")
async def callback_plans_menu(callback: CallbackQuery):
    await safe_answer_callback(callback)
    await show_plans(callback.message, callback.from_user.id)

@router.callback_query(F.data == "plan_add")
async def callback_plan_add(callback: CallbackQuery):
    await safe_answer_callback(callback, "Введите название плана в следующем сообщении")
    try:
        await callback.message.edit_text(
            '📋 <b>Создание плана</b>\n\n'
            '✍️ <b>Шаг 1: Введите название плана</b>\n\n'
            'Просто отправьте текст с названием плана.\n'
            'Например: "Вышить 10000 крестиков к Новому году"',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    except:
        await callback.message.answer(
            '📋 <b>Создание плана</b>\n\n'
            '✍️ <b>Шаг 1: Введите название плана</b>\n\n'
            'Просто отправьте текст с названием плана.\n'
            'Например: "Вышить 10000 крестиков к Новому году"',
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    pending_plans[callback.from_user.id] = {'step': 'name'}

@router.callback_query(F.data.startswith("plan_"))
async def callback_plan(callback: CallbackQuery):
    await safe_answer_callback(callback)
    plan_id = callback.data.replace("plan_", "")
    if plan_id.startswith("delete_"):
        plan_id = plan_id.replace("delete_", "")
        delete_plan(plan_id, callback.from_user.id)
        await callback.message.answer('✅ План удален', reply_markup=get_back_keyboard())
        await show_plans(callback.message, callback.from_user.id)
    else:
        await show_plan(callback.message, callback.from_user.id, plan_id)

def clear_pending_plan(user_id: int):
    if user_id in pending_plans:
        del pending_plans[user_id]

