"""Redis client configuration and utilities."""

import redis.asyncio as redis
from typing import Optional
from .config import settings

# Create async Redis client (lazy initialization)
_redis_client = None

def get_redis_client() -> redis.Redis:
    """Get Redis client instance with lazy initialization."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.redis_url)
        except Exception as e:
            print(f"Warning: Could not create Redis client: {e}")
            _redis_client = None
    return _redis_client


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client instance."""
    return _redis_client


# Project lock management
def acquire_project_lock(project_id: int, agent_name: str, ttl_seconds: int = 300) -> bool:
    """Acquire a lock for processing a project."""
    if not redis_client:
        return True  # Allow processing if Redis is unavailable

    key = f"lock:project:{project_id}"
    value = f"{agent_name}:{settings.redis_url.split('/')[-1]}"  # Include worker ID

    # Use SET with NX to only set if key doesn't exist
    return redis_client.set(key, value, ex=ttl_seconds, nx=True)


def release_project_lock(project_id: int, agent_name: str) -> bool:
    """Release a project lock."""
    if not redis_client:
        return True

    key = f"lock:project:{project_id}"
    current_value = redis_client.get(key)

    if current_value and current_value.decode().startswith(agent_name):
        redis_client.delete(key)
        return True

    return False


def renew_project_lock(project_id: int, agent_name: str, ttl_seconds: int = 300) -> bool:
    """Renew a project lock."""
    if not redis_client:
        return True

    key = f"lock:project:{project_id}"
    current_value = redis_client.get(key)

    if current_value and current_value.decode().startswith(agent_name):
        redis_client.expire(key, ttl_seconds)
        return True

    return False


# Email deduplication
async def check_email_deduplication(email_key: str) -> bool:
    """Check if email was recently sent."""
    redis_client = get_redis_client()
    if not redis_client:
        return False

    key = f"email_sent:{email_key}"
    exists = await redis_client.exists(key)
    return bool(exists)


async def mark_email_sent(email_key: str, ttl_seconds: int = 172800) -> None:
    """Mark email as sent for deduplication."""
    redis_client = get_redis_client()
    if redis_client:
        key = f"email_sent:{email_key}"
        await redis_client.setex(key, ttl_seconds, "1")


# Thread tracking
async def store_email_thread(thread_id: str, thread_data: dict, ttl_seconds: int = 604800) -> None:
    """Store email thread information."""
    redis_client = get_redis_client()
    if redis_client:
        key = f"thread:{thread_id}"
        await redis_client.setex(key, ttl_seconds, json.dumps(thread_data))


async def get_email_thread(thread_id: str) -> Optional[dict]:
    """Retrieve email thread information."""
    redis_client = get_redis_client()
    if not redis_client:
        return None

    key = f"thread:{thread_id}"
    data = await redis_client.get(key)

    if data:
        try:
            thread_dict = json.loads(data.decode())
            return thread_dict
        except:
            return None

    return None


# Work queue management
async def add_to_work_queue(work_item: str, priority: int = 50) -> None:
    """Add item to priority work queue."""
    redis_client = get_redis_client()
    if redis_client:
        await redis_client.zadd("work_queue", {work_item: priority})


async def get_work_queue_length() -> int:
    """Get work queue length."""
    redis_client = get_redis_client()
    if not redis_client:
        return 0

    return await redis_client.zcard("work_queue")


# Cache management
async def cache_get(key: str) -> Optional[str]:
    """Get value from cache."""
    redis_client = get_redis_client()
    if not redis_client:
        return None

    value = await redis_client.get(key)
    return value.decode() if value else None


async def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Set value in cache."""
    redis_client = get_redis_client()
    if redis_client:
        await redis_client.setex(key, ttl_seconds, value)


async def cache_delete(key: str) -> None:
    """Delete value from cache."""
    redis_client = get_redis_client()
    if redis_client:
        await redis_client.delete(key)


# Health check
async def redis_health_check() -> dict:
    """Check Redis health."""
    redis_client = get_redis_client()
    if not redis_client:
        return {"status": "unavailable", "error": "Redis client not initialized"}

    try:
        await redis_client.ping()
        info = await redis_client.info()
        return {
            "status": "healthy",
            "version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "uptime_days": info.get("uptime_in_days")
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
