import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from config import BOT_TOKEN
from data.storage import is_subscribed
from handlers import commands, entries, statistics, projects, delete, hashtags, wishlist, notes, plans, calendar, challenges, subscriptions, period_comparison, export, admin, feedback
from handlers.keyboards import get_main_menu

# Создаем директорию для логов, если её нет
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

# Настройка логирования в файл и консоль
log_file = os.path.join(log_dir, 'bot.log')
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10*1024*1024,  # 10 МБ
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)  # DEBUG для файла - больше деталей
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)  # INFO для консоли
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.DEBUG,  # DEBUG для корневого логгера
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрация middleware для отслеживания пользователей
from middleware.user_tracker import UserTrackerMiddleware
dp.message.outer_middleware(UserTrackerMiddleware())
dp.callback_query.outer_middleware(UserTrackerMiddleware())

# Регистрация роутеров
dp.include_router(commands.router)
dp.include_router(entries.router)  # Роутер для обработки кнопок добавления крестиков
dp.include_router(statistics.router)
dp.include_router(projects.router)
dp.include_router(delete.router)
dp.include_router(hashtags.router)
dp.include_router(wishlist.router)
dp.include_router(notes.router)
dp.include_router(plans.router)
dp.include_router(calendar.router)
dp.include_router(challenges.router)
dp.include_router(subscriptions.router)
dp.include_router(period_comparison.router)
dp.include_router(export.router)
dp.include_router(admin.router)
dp.include_router(feedback.router)

# Обработка текстовых сообщений (для диалогов)
@dp.message(lambda msg: msg.text and not msg.text.startswith('/'))
async def handle_text_messages(message: Message):
    user_id = message.from_user.id
    
    # Логируем входящее текстовое сообщение
    logger.info(f"[BOT] Получено текстовое сообщение от user_id={user_id}, text='{message.text[:100] if message.text else 'None'}'")
    
    # Проверяем подписку, но не блокируем полностью - проверяем, есть ли активные диалоги
    subscribed = is_subscribed(user_id)
    logger.info(f"[BOT] Проверка подписки для user_id={user_id}, subscribed={subscribed}")
    if not subscribed:
        # Проверяем, есть ли активные диалоги, которые нужно завершить
        has_active_dialog = (
            user_id in entries.pending_entries or
            user_id in projects.pending_projects or
            user_id in delete.pending_deletes or
            user_id in wishlist.pending_wishlist or
            user_id in notes.pending_notes or
            user_id in plans.pending_plans
        )
        
        if not has_active_dialog:
            # Если нет активных диалогов, сообщаем об истекшей подписке
            logger.info(f"[BOT] Подписка истекла для user_id={user_id}, нет активных диалогов - блокируем")
            try:
                from handlers.keyboards import get_main_menu
                await message.answer(
                    '🔒 <b>Подписка истекла</b>\n\n'
                    'Для использования бота необходима активная подписка.\n\n'
                    'Используйте кнопку "💳 Подписка" для оформления.',
                    parse_mode='HTML',
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                logger.error(f"[BOT] Ошибка при отправке сообщения об истекшей подписке: {e}", exc_info=True)
            return
        # Если есть активный диалог, разрешаем его завершить
        logger.info(f"[BOT] Подписка истекла для user_id={user_id}, но есть активный диалог - разрешаем обработку")
    
    # Обрабатываем диалоги в порядке приоритета
    # Сначала проверяем активные диалоги (те, что требуют текстового ввода)
    
    # Обрабатываем диалог добавления крестиков (самый частый)
    try:
        result = await entries.process_entry_message(message, user_id)
        if result:
            logger.info(f"[BOT] Сообщение обработано в process_entry_message, результат: {result}")
            return
    except Exception as e:
        logger.error(f"[BOT] Ошибка в process_entry_message: {e}", exc_info=True)
    
    # Обрабатываем диалог планов
    try:
        result = await plans.process_plan_message(message, user_id)
        if result:
            logger.info(f"[BOT] Сообщение обработано в process_plan_message, результат: {result}")
            return
    except Exception as e:
        logger.error(f"[BOT] Ошибка в process_plan_message: {e}", exc_info=True)
    
    # Обрабатываем диалог добавления проекта
    try:
        if await projects.process_project_message(message, user_id):
            return
    except Exception as e:
        logger.error(f"[BOT] Ошибка в process_project_message: {e}", exc_info=True)
    
    # Обрабатываем диалог удаления
    try:
        if await delete.process_delete_message(message, user_id):
            return
    except Exception as e:
        logger.error(f"[BOT] Ошибка в process_delete_message: {e}", exc_info=True)
    
    # Обрабатываем диалог вишлиста
    try:
        if await wishlist.process_wishlist_message(message, user_id):
            return
    except Exception as e:
        logger.error(f"[BOT] Ошибка в process_wishlist_message: {e}", exc_info=True)
    
    # Обрабатываем диалог заметок
    try:
        if await notes.process_note_message(message, user_id):
            logger.info(f"[BOT] Сообщение обработано в process_note_message")
            return
    except Exception as e:
        logger.error(f"[BOT] Ошибка в process_note_message: {e}", exc_info=True)
    
    # Если сообщение не обработано ни одним диалогом, проверяем состояние
    logger.info(f"[BOT] Сообщение не обработано ни одним диалогом, user_id={user_id}")
    logger.info(f"[BOT] pending_entries: {list(entries.pending_entries.keys())}")
    logger.info(f"[BOT] pending_projects: {list(projects.pending_projects.keys())}")
    logger.info(f"[BOT] pending_plans: {list(plans.pending_plans.keys())}")
    logger.info(f"[BOT] pending_notes: {list(notes.pending_notes.keys())}")
    logger.info(f"[BOT] pending_wishlist: {list(wishlist.pending_wishlist.keys())}")
    
    # Если пользователь не в активном диалоге, показываем главное меню
    if subscribed:
        try:
            from handlers.keyboards import get_main_menu
            await message.answer(
                '💬 Я не понял ваше сообщение.\n\n'
                'Используйте кнопки меню для работы с ботом.',
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logger.error(f"[BOT] Ошибка при отправке сообщения: {e}", exc_info=True)

# Обработка фотографий
@dp.message(lambda msg: msg.photo is not None)
async def handle_photos(message: Message):
    user_id = message.from_user.id
    
    if not is_subscribed(user_id):
        return
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    
    # Проверяем, идет ли диалог добавления проекта
    if await projects.process_project_photo(message, user_id, photo.file_id):
        return

# Команда отмены
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    user_id = message.from_user.id
    entries.clear_pending(user_id)
    projects.clear_pending_project(user_id)
    delete.clear_pending_delete(user_id)
    wishlist.clear_pending_wishlist(user_id)
    notes.clear_pending_note(user_id)
    plans.clear_pending_plan(user_id)
    await message.answer('❌ Отменено', reply_markup=get_main_menu())

async def main():
    logger.info("🤖 Запуск бота...")
    try:
        # Фоновая задача для проверки подписок
        from handlers.subscription_notifications import subscription_checker_task
        task = asyncio.create_task(subscription_checker_task(bot))
        logger.info("✅ Фоновая задача проверки подписок запущена")
        
        logger.info("Подключение к Telegram API...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        raise
    finally:
        # Отменяем фоновую задачу при остановке (если она была запущена)
        if 'task' in locals():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await bot.session.close()

if __name__ == '__main__':
    try:
        logger.info("Инициализация...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        print("Проверьте:")
        print("1. Файл .env существует и содержит BOT_TOKEN")
        print("2. Токен бота правильный")
        print("3. Установлены все зависимости: pip install -r requirements.txt")
        input("\nНажмите Enter для выхода...")

