import asyncio
import os
import logging
import sqlite3
from aiohttp import web, ClientSession
from config import BOT_TOKEN, CHANNEL_ID, CHECK_INTERVAL
from parser import fetch_kwork_orders

# Настройка логирования под формат твоих скриншотов
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger(__name__)

# =====================================================================
# БЛОК РАБОТЫ С БАЗОЙ ДАННЫХ
# =====================================================================
def init_db():
    """Создает базу данных и таблицу для заказов, если их нет"""
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized.")

def is_new_order(order_id) -> bool:
    """Проверяет, нет ли ордера в нашей базе данных"""
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,))
    result = cursor.fetchone()
    conn.close()
    return result is None

def save_order(order_id):
    """Сохраняет ID заказа в базу, чтобы не слать его повторно"""
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (id) VALUES (?)", (order_id,))
    conn.commit()
    conn.close()

# =====================================================================
# БЛОК УВЕДОМЛЕНИЙ В TELEGRAM
# =====================================================================
async def send_telegram_notification(session: ClientSession, order: dict):
    """Отправляет структурированную карточку заказа в твой канал"""
    text = (
        f"🔔 *Новый заказ на Kwork!*\n\n"
        f"📌 *{order['title']}*\n"
        f"💰 *Цена:* {order['price']}\n\n"
        f"📝 *Описание:* {order['description']}\n\n"
        f"🔗 [Открыть заказ на бирже]({order['url']})"
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                logger.info(f"New order notified: {order['id']}")
            else:
                logger.error(f"Ошибка отправки в Telegram (Код: {resp.status})")
    except Exception as e:
        logger.error(f"Не удалось связаться с API Telegram: {e}")

# =====================================================================
# БЕСКОНЕЧНЫЙ ЦИКЛ МОНИТОРИНГА ТАКСОВ
# =====================================================================
async def monitoring_loop():
    """Основной фоновый движок парсинга"""
    init_db()
    
    # Создаем одну сессию для отправки уведомлений в TG
    async with ClientSession() as session:
        while True:
            try:
                logger.info("Start checking for new orders...")
                
                # Запускаем наш ультимативный парсер
                orders = await fetch_kwork_orders(session)
                logger.info(f"Checked. {len(orders)} orders found.")
                
                for order in orders:
                    if is_new_order(order["id"]):
                        # Отправляем уведомление
                        await send_telegram_notification(session, order)
                        # Кэшируем в локальную БД
                        save_order(order["id"])
                        # Крошечный тайм-аут, чтобы телега не спамила лимитами
                        await asyncio.sleep(1)
                        
            except Exception as e:
                logger.error(f"Критический сбой в цикле мониторинга: {e}")
            
            # Ждем интервал перед следующим кругом сканирования Kwork
            await asyncio.sleep(int(CHECK_INTERVAL))

# =====================================================================
# ХЭНДЛЕР ДЛЯ RENDER (HEALTH CHECK)
# =====================================================================
async def handle_health_check(request):
    """Сюда будет стучаться Render и UptimeRobot, проверяя жив ли бот"""
    return web.Response(text="Kwork Parser Bot status: ACTIVE", status=200)

# =====================================================================
# ГЛАВНАЯ ТОЧКА ЗАПУСКА ПРИЛОЖЕНИЯ
# =====================================================================
async def main():
    # 1. Запускаем бесконечный парсер в фоновой асинхронной задаче
    asyncio.create_task(monitoring_loop())
    
    # 2. Поднимаем веб-сервер на параллельных рельсах
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    
    # Render выдает порт динамически. Если запускаешь локально — включится 8080
    port = int(os.getenv("PORT", 8080))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    logger.info(f"Стартуем веб-сервер на порту {port} для удовлетворения Render...")
    await site.start()
    
    # Удерживаем приложение от завершения работы
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот успешно остановлен разработчиком.")