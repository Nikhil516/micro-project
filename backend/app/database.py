from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


async def connect() -> AsyncIOMotorDatabase:
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    db = _client[settings.database_name]
    await db.users.create_index("email", unique=True)
    await db.products.create_index("product_id", unique=True)
    await db.products.create_index("category")
    await db.sales.create_index([("product_id", 1), ("date", 1)])
    await db.forecasts.create_index([("product_id", 1), ("week_start", -1)])
    await db.token_blocklist.create_index("exp", expireAfterSeconds=0)
    await db.inventory.create_index("product_id", unique=True)
    await db.model_metrics.create_index("model_version")
    return db


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client is not connected")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.database_name]


async def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
