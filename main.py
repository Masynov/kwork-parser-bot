import asyncio
import logging
import aiohttp
import config
from database import init_db, is_order_sent, save_order
from parser import fetch_kwork_orders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def send_notification(session: aiohttp.ClientSession, order: dict):
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    message_text = (
        f"🔥 <b>New Order on Kwork!</b>\n\n"
        f"📌 <b>Title:</b> {order['title']}\n"
        f"💰 <b>Budget:</b> {order['price']}\n\n"
        f"📝 <b>Description:</b>\n{order['description']}\n\n"
        f"🔗 <a href='{order['url']}'>Respond to Order</a>"
    )
    payload = {
        "chat_id": config.CHANNEL_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                logger.error(f"Telegram API error: {await response.text()}")
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")

async def monitor_loop():
    await init_db()
    logger.info("Database initialized. Monitoring loop started...")
    
    async with aiohttp.ClientSession() as session:
        while True:
            logger.info("Checking for new orders...")
            orders = await fetch_kwork_orders(session)
            logger.info(f"Найдено заказов на странице: {len(orders)}")
            
            # Process from oldest to newest
            for order in reversed(orders):
                if not await is_order_sent(order["id"]):
                    await send_notification(session, order)
                    await save_order(order["id"])
                    logger.info(f"New order notified: {order['id']}")
                    await asyncio.sleep(1)
            
            await asyncio.sleep(config.CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Parser stopped manually.")