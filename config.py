import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATA_DIR = os.getenv('DATA_DIR', './data')
# Флаг тестового режима (пока оплата не нужна)
TEST_MODE = os.getenv('TEST_MODE', 'True').lower() == 'true'
# ID подписки из BotFather (будет настроено позже)
SUBSCRIPTION_ID = os.getenv('SUBSCRIPTION_ID', '')
# ID администраторов (через запятую, например: "123456789,987654321")
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(uid.strip()) for uid in ADMIN_IDS_STR.split(',') if uid.strip()] if ADMIN_IDS_STR else []

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле!")

