import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
KWORK_URL = os.getenv("KWORK_URL", "https://kwork.ru/projects")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))

if not BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("BOT_TOKEN and CHANNEL_ID must be set in environmental variables!")