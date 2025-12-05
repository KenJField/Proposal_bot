"""Redis client configuration and utilities."""

import redis
from .config import settings

# Create Redis client
redis_client = redis.from_url(settings.redis_url)

# Test connection
try:
    redis_client.ping()
except redis.ConnectionError:
    print("Warning: Could not connect to Redis")
    redis_client = None


def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    return redis_client


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
def check_email_deduplication(email_key: str) -> bool:
    """Check if email was recently sent."""
    if not redis_client:
        return False

    key = f"email_sent:{email_key}"
    return bool(redis_client.exists(key))


def mark_email_sent(email_key: str, ttl_seconds: int = 172800) -> None:
    """Mark email as sent for deduplication."""
    if redis_client:
        key = f"email_sent:{email_key}"
        redis_client.setex(key, ttl_seconds, "1")


# Thread tracking
def store_email_thread(thread_id: str, thread_data: dict, ttl_seconds: int = 604800) -> None:
    """Store email thread information."""
    if redis_client:
        key = f"thread:{thread_id}"
        redis_client.setex(key, ttl_seconds, str(thread_data))


def get_email_thread(thread_id: str) -> Optional[dict]:
    """Retrieve email thread information."""
    if not redis_client:
        return None

    key = f"thread:{thread_id}"
    data = redis_client.get(key)

    if data:
        try:
            return eval(data.decode())  # In production, use JSON
        except:
            return None

    return None


# Work queue management
def add_to_work_queue(work_item: str, priority: int = 50) -> None:
    """Add item to priority work queue."""
    if redis_client:
        redis_client.zadd("work_queue", {work_item: priority})


def get_work_queue_length() -> int:
    """Get work queue length."""
    if not redis_client:
        return 0

    return redis_client.zcard("work_queue")


# Cache management
def cache_get(key: str) -> Optional[str]:
    """Get value from cache."""
    if not redis_client:
        return None

    value = redis_client.get(key)
    return value.decode() if value else None


def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Set value in cache."""
    if redis_client:
        redis_client.setex(key, ttl_seconds, value)


def cache_delete(key: str) -> None:
    """Delete value from cache."""
    if redis_client:
        redis_client.delete(key)


# Health check
def redis_health_check() -> dict:
    """Check Redis health."""
    if not redis_client:
        return {"status": "unavailable", "error": "Redis client not initialized"}

    try:
        redis_client.ping()
        info = redis_client.info()
        return {
            "status": "healthy",
            "version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "uptime_days": info.get("uptime_in_days")
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
