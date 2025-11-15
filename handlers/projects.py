from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from data.storage import get_projects, save_project, remove_project_photo, delete_project
from handlers.keyboards import get_back_keyboard, get_project_navigation
from utils import safe_answer_callback
import os

router = Router()

DATA_DIR = os.getenv('DATA_DIR', './data')
os.makedirs(os.path.join(DATA_DIR, 'images'), exist_ok=True)

pending_projects = {}
pending_photo_updates = {}  # Для обновления фото существующих проектов

async def add_project_dialog(message: Message, user_id: int):
    await message.answer(
        '📝 <b>Добавление новой работы</b>\n\n'
        'Введите название работы:',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )
    pending_projects[user_id] = {'step': 'name'}

async def process_project_message(message: Message, user_id: int):
    if user_id not in pending_projects:
        return False
    
    state = pending_projects[user_id]
    
    if state['step'] == 'name':
        name = message.text.strip()
        if not name:
            await message.answer('❌ Название не может быть пустым', reply_markup=get_back_keyboard())
            return True
        
        state['name'] = name
        state['step'] = 'photo'
        await message.answer(
            f'✅ Название: {name}\n\n'
            'Отправьте фото работы (или отправьте "пропустить"):',
            reply_markup=get_back_keyboard()
        )
        return True
    
    elif state['step'] == 'photo':
        text = message.text.strip().lower()
        if text == 'пропустить' or text == 'skip':
            # Переходим к хэштегу без фото
            state['step'] = 'hashtag'
            await message.answer(
                f'✅ Название: {state["name"]}\n\n'
                'Введите хэштег для этой работы (или отправьте "пропустить"):',
                reply_markup=get_back_keyboard()
            )
            return True
    
    elif state['step'] == 'hashtag':
        hashtag = message.text.strip()
        if hashtag.lower() == 'пропустить' or hashtag.lower() == 'skip':
            hashtag = None
        else:
            # Убираем # если пользователь его добавил
            hashtag = hashtag.lstrip('#').strip()
            if not hashtag:
                hashtag = None
        
        # Сохраняем проект
        project = {
            'id': f"project-{user_id}-{int(datetime.now().timestamp())}",
            'name': state['name'],
            'userId': user_id
        }
        if 'imageFileId' in state:
            project['imageFileId'] = state['imageFileId']
        if hashtag:
            project['hashtag'] = hashtag
        
        save_project(project)
        
        result_text = f'✅ <b>Работа добавлена!</b>\n\nНазвание: {project["name"]}'
        if hashtag:
            result_text += f'\nХэштег: #{hashtag}'
        
        await message.answer(
            result_text,
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
        del pending_projects[user_id]
        return True
    
    return False

async def process_project_photo(message: Message, user_id: int, photo_file_id: str):
    # Проверяем, обновляется ли фото существующего проекта
    if user_id in pending_photo_updates:
        project_id = pending_photo_updates[user_id]
        projects = get_projects(user_id)
        project = next((p for p in projects if p.get('id') == project_id), None)
        
        if project:
            # Обновляем фото проекта
            project['imageFileId'] = photo_file_id
            save_project(project)
            
            # Находим индекс проекта для обновления отображения
            projects_list = get_projects(user_id)
            projects_list.reverse()
            project_index = None
            for i, p in enumerate(projects_list):
                if p.get('id') == project_id:
                    project_index = i
                    break
            
            del pending_photo_updates[user_id]
            
            if project_index is not None:
                await message.answer('✅ Фото обновлено!', reply_markup=get_back_keyboard())
                await show_project_by_index(message, user_id, project_index, is_edit=False)
            else:
                await message.answer('✅ Фото обновлено!', reply_markup=get_back_keyboard())
        else:
            del pending_photo_updates[user_id]
            await message.answer('❌ Проект не найден', reply_markup=get_back_keyboard())
        return True
    
    # Обработка фото для нового проекта
    if user_id not in pending_projects:
        return False
    
    state = pending_projects[user_id]
    
    if state['step'] == 'photo' and 'name' in state:
        # Сохраняем фото и переходим к хэштегу
        state['imageFileId'] = photo_file_id
        state['step'] = 'hashtag'
        await message.answer(
            f'✅ Название: {state["name"]}\n'
            f'✅ Фото добавлено\n\n'
            'Введите хэштег для этой работы (или отправьте "пропустить"):',
            reply_markup=get_back_keyboard()
        )
        return True
    
    return False

async def show_projects(message: Message, user_id: int, index: int = 0):
    projects_list = get_projects(user_id)
    
    if not projects_list:
        await message.answer('📝 У вас пока нет работ.', reply_markup=get_back_keyboard())
        return
    
    await show_project_by_index(message, user_id, index)

async def show_project_by_index(message, user_id: int, index: int, is_edit: bool = False):
    """Универсальная функция для показа проекта с поддержкой редактирования"""
    projects_list = get_projects(user_id)
    projects_list.reverse()
    
    if not projects_list or index < 0 or index >= len(projects_list):
        return
    
    project = projects_list[index]
    text = f'<b>📸 {project["name"]}</b>\n\n'
    
    if project.get('hashtag'):
        text += f"#️⃣ Хэштег: #{project['hashtag']}\n"
    
    if project.get('startDate'):
        try:
            date_obj = datetime.strptime(project['startDate'], '%Y-%m-%d')
            text += f"📅 Начато: {date_obj.strftime('%d %B %Y')}\n"
        except:
            pass
    
    text += f"\n{index + 1} из {len(projects_list)}"
    has_photo = bool(project.get('imageFileId'))
    navigation = get_project_navigation(index, len(projects_list), project.get('id'), has_photo)
    
    if project.get('imageFileId'):
        if is_edit and message.photo:
            # Редактируем существующее фото
            from aiogram.types import InputMediaPhoto
            try:
                await message.edit_media(
                    media=InputMediaPhoto(media=project['imageFileId'], caption=text),
                    reply_markup=navigation
                )
            except:
                # Если не получилось отредактировать, отправляем новое
                await message.answer_photo(
                    project['imageFileId'],
                    caption=text,
                    parse_mode='HTML',
                    reply_markup=navigation
                )
        else:
            await message.answer_photo(
                project['imageFileId'],
                caption=text,
                parse_mode='HTML',
                reply_markup=navigation
            )
    else:
        if is_edit:
            try:
                await message.edit_text(text, parse_mode='HTML', reply_markup=navigation)
            except:
                await message.answer(text, parse_mode='HTML', reply_markup=navigation)
        else:
            await message.answer(text, parse_mode='HTML', reply_markup=navigation)

@router.callback_query(F.data.startswith("project_prev_"))
async def callback_project_prev(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    index = int(callback.data.split('_')[-1])
    if index > 0:
        await show_project_by_index(callback.message, user_id, index - 1, is_edit=True)

@router.callback_query(F.data.startswith("project_next_"))
async def callback_project_next(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    index = int(callback.data.split('_')[-1])
    projects_list = get_projects(user_id)
    if index < len(projects_list) - 1:
        await show_project_by_index(callback.message, user_id, index + 1, is_edit=True)

@router.callback_query(F.data.startswith("project_change_photo_"))
async def callback_change_project_photo(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    project_id = callback.data.replace("project_change_photo_", "")
    
    # Проверяем, существует ли проект
    projects = get_projects(user_id)
    project = next((p for p in projects if p.get('id') == project_id), None)
    
    if not project:
        await callback.message.answer('❌ Проект не найден', reply_markup=get_back_keyboard())
        return
    
    # Сохраняем project_id для обработки фото
    pending_photo_updates[user_id] = project_id
    
    has_photo = bool(project.get('imageFileId'))
    action_text = "изменить" if has_photo else "добавить"
    
    await callback.message.answer(
        f'📸 <b>{action_text.capitalize()} фото</b>\n\n'
        f'Проект: <b>{project.get("name")}</b>\n\n'
        'Отправьте новое фото для этой работы:',
        parse_mode='HTML',
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data.startswith("project_delete_photo_"))
async def callback_delete_project_photo(callback: CallbackQuery):
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    project_id = callback.data.replace("project_delete_photo_", "")
    
    # Удаляем фото
    if remove_project_photo(project_id, user_id):
        # Находим индекс проекта для обновления отображения
        projects_list = get_projects(user_id)
        projects_list.reverse()
        project_index = None
        for i, p in enumerate(projects_list):
            if p.get('id') == project_id:
                project_index = i
                break
        
        if project_index is not None:
            # Если сообщение было с фото, удаляем его и отправляем новое текстовое
            if callback.message.photo:
                try:
                    await callback.message.delete()
                except:
                    pass
                await callback.message.answer('✅ Фото удалено', reply_markup=get_back_keyboard())
            else:
                try:
                    await callback.message.edit_text('✅ Фото удалено', reply_markup=get_back_keyboard())
                except:
                    await callback.message.answer('✅ Фото удалено', reply_markup=get_back_keyboard())
            
            # Показываем обновленный проект (теперь без фото)
            await show_project_by_index(callback.message, user_id, project_index, is_edit=False)
    else:
        await callback.message.answer('❌ Не удалось удалить фото', reply_markup=get_back_keyboard())

@router.callback_query(F.data.startswith("project_delete_"))
async def callback_delete_project(callback: CallbackQuery):
    """Обработчик удаления проекта"""
    await safe_answer_callback(callback)
    user_id = callback.from_user.id
    
    # Пропускаем, если это удаление фото
    if callback.data.startswith("project_delete_photo_"):
        return
    
    project_id = callback.data.replace("project_delete_", "")
    
    # Проверяем, что проект существует и принадлежит пользователю
    projects = get_projects(user_id)
    project = next((p for p in projects if p.get('id') == project_id), None)
    
    if not project:
        await callback.message.answer('❌ Проект не найден', reply_markup=get_back_keyboard())
        return
    
    # Удаляем проект
    if delete_project(project_id, user_id):
        project_name = project.get('name', 'Работа')
        
        # Пытаемся удалить сообщение с проектом
        try:
            if callback.message.photo:
                await callback.message.delete()
            else:
                await callback.message.delete()
        except:
            pass
        
        # Показываем обновленный список проектов
        projects_list = get_projects(user_id)
        if projects_list:
            # Показываем первый проект из списка
            projects_list.reverse()
            await show_project_by_index(callback.message, user_id, 0, is_edit=False)
        else:
            # Если проектов не осталось, показываем сообщение
            await callback.message.answer(
                f'✅ Работа "{project_name}" удалена\n\n📝 У вас пока нет работ.',
                reply_markup=get_back_keyboard()
            )
    else:
        await callback.message.answer('❌ Не удалось удалить работу', reply_markup=get_back_keyboard())

def clear_pending_project(user_id: int):
    if user_id in pending_projects:
        del pending_projects[user_id]
    if user_id in pending_photo_updates:
        del pending_photo_updates[user_id]

