from loguru import logger
from redis.asyncio import Redis
from starsessions.stores.redis import RedisStore
from starlette.applications import Starlette

from app.config import Settings


def setup_session_store(app: Starlette, settings: Settings) -> None:
    """Create the Redis session store without performing I/O."""

    if getattr(app.state, "session_store", None) is not None:
        return

    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    session_store = RedisStore(connection=redis, prefix="session:")
    app.state.redis = redis
    app.state.session_store = session_store


async def init_session_store(app: Starlette, settings: Settings) -> None:
    """Initialize Redis session store; fail startup if Redis is unavailable."""

    setup_session_store(app, settings)
    redis = app.state.redis
    try:
        await redis.ping()
    except Exception:
        await redis.close()
        logger.exception("Redis session store unavailable")
        raise

    session_store = RedisStore(connection=redis, prefix="session:")
    app.state.redis = redis
    logger.info("Redis client registered on app.state")
    app.state.session_store = session_store
    logger.info("Redis session store registered on app.state")


async def close_session_store(app: Starlette) -> None:
    """Close Redis session store connection if it exists."""

    redis = getattr(app.state, "redis", None)
    if redis is None:
        return

    await redis.close()
    logger.info("Redis client closed")
    app.state.redis = None
    delattr(app.state, "redis")
    app.state.session_store = None
    delattr(app.state, "session_store")
    logger.info("Redis session store unregistered from app.state")


def get_session_store(app: Starlette) -> RedisStore:
    """Return the initialized session store or raise if missing."""

    session_store = getattr(app.state, "session_store", None)
    if session_store is None:
        raise RuntimeError("Session store is not initialized")

    return session_store
