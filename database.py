import aiosqlite

DB_NAME = "orders.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_orders (
                id TEXT PRIMARY KEY
            )
        """)
        await db.commit()

async def is_order_sent(order_id: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT 1 FROM sent_orders WHERE id = ?", (order_id,)) as cursor:
            result = await cursor.fetchone()
            return result is not None

async def save_order(order_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO sent_orders (id) VALUES (?)", (order_id,))
        await db.commit()