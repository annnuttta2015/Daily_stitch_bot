import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from config import BOT_TOKEN
from data.storage import is_subscribed
from handlers import commands, entries, statistics, projects, delete, hashtags, wishlist, notes, plans, calendar, challenges, subscriptions, period_comparison, export
from handlers.keyboards import get_main_menu

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

# Обработка текстовых сообщений (для диалогов)
@dp.message(lambda msg: msg.text and not msg.text.startswith('/'))
async def handle_text_messages(message: Message):
    user_id = message.from_user.id
    
    if not is_subscribed(user_id):
        return
    
    # Обрабатываем диалог добавления крестиков
    if await entries.process_entry_message(message, user_id):
        return
    
    # Обрабатываем диалог добавления проекта
    if await projects.process_project_message(message, user_id):
        return
    
    # Обрабатываем диалог удаления
    if await delete.process_delete_message(message, user_id):
        return
    
    # Обрабатываем диалог вишлиста
    if await wishlist.process_wishlist_message(message, user_id):
        return
    
    # Обрабатываем диалог заметок
    if await notes.process_note_message(message, user_id):
        return
    
    # Обрабатываем диалог планов
    if await plans.process_plan_message(message, user_id):
        return

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
        logger.info("Подключение к Telegram API...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        raise
    finally:
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

