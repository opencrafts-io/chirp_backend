"""
Cache Service for Post Recommendations
"""

import json
import logging
from typing import List, Optional, Any, Dict
from django.core.cache import cache
from django.conf import settings
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RecommendationCacheService:
    """
    service for caching recommendation data.
    """

    def __init__(self):
        self.cache_prefix = "recommendations"
        self.default_timeout = 300
        self.user_timeout = 600
        self.redis_client = self._get_redis_client()
        self.key_tracker = set()

    def _get_redis_client(self):
        """Get Redis client for advanced operations."""
        try:
            cache_config = settings.CACHES.get('default', {})
            if 'redis' in cache_config.get('BACKEND', '').lower():

                location = cache_config.get('LOCATION', 'redis://127.0.0.1:6379/1')
                return redis.from_url(location, decode_responses=True)
            return None
        except Exception as e:
            logger.warning(f"Redis client not available: {e}")
            return None

    def get_recommendations(
        self,
        user_id: Optional[str] = None,
        group_id: Optional[int] = None,
        limit: int = 20
    ) -> Optional[List[Dict]]:
        """
        Get cached recommendations

        Args:
            user_id: User ID for personalized recommendations
            group_id: Specific group to filter posts
            limit: Maximum number of posts to return

        Returns:
            Cached recommendation data or None
        """
        try:
            cache_key = self._generate_cache_key(user_id, group_id, limit)

            if self.redis_client:
                try:
                    cached_data = self.redis_client.get(cache_key)
                    if cached_data:
                        logger.debug(f"Redis cache hit for key: {cache_key}")
                        return json.loads(cached_data)
                except RedisError as e:
                    logger.warning(f"Redis error, falling back to Django cache: {e}")

            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"Django cache hit for key: {cache_key}")
                return json.loads(cached_data) if isinstance(cached_data, str) else cached_data

            logger.debug(f"Cache miss for key: {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving cache: {str(e)}")
            return None

    def set_recommendations(
        self,
        recommendations: List[Dict],
        user_id: Optional[str] = None,
        group_id: Optional[int] = None,
        limit: int = 20,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Cache recommendations Redis and Django cache support.

        Args:
            recommendations: List of recommendation data to cache
            user_id: User ID for personalized recommendations
            group_id: Specific group to filter posts
            limit: Maximum number of posts to return
            timeout: Cache timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(user_id, group_id, limit)

            if timeout is None:
                timeout = self.user_timeout if user_id else self.default_timeout

            serialized_data = json.dumps(recommendations, default=str)

            success = True

            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, timeout, serialized_data)
                    logger.debug(f"Stored in Redis: {cache_key}")
                except RedisError as e:
                    logger.warning(f"Redis storage failed: {e}")
                    success = False

            try:
                cache.set(cache_key, serialized_data, timeout)
                logger.debug(f"Stored in Django cache: {cache_key}")
            except Exception as e:
                logger.error(f"Django cache storage failed: {e}")
                success = False

            self.key_tracker.add(cache_key)

            logger.debug(f"Cached recommendations for key: {cache_key}")
            return success

        except Exception as e:
            logger.error(f"Error caching recommendations: {str(e)}")
            return False

    def invalidate_user_cache(self, user_id: str) -> bool:
        """
        Invalidate all cache entries for a specific user using Redis SCAN.

        Args:
            user_id: User ID to invalidate cache for

        Returns:
            True if successful, False otherwise
        """
        try:
            pattern = f"{self.cache_prefix}:user_{user_id}:*"
            deleted_count = 0

            if self.redis_client:
                try:
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            deleted_count += self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                    logger.info(f"Invalidated {deleted_count} Redis keys for user: {user_id}")
                except RedisError as e:
                    logger.error(f"Redis invalidation failed: {e}")
                    return False

            django_deleted = 0
            keys_to_remove = set()
            for key in self.key_tracker.copy():
                if f"user_{user_id}" in key:
                    try:
                        cache.delete(key)
                        keys_to_remove.add(key)
                        django_deleted += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete Django cache key {key}: {e}")

            self.key_tracker -= keys_to_remove

            total_deleted = deleted_count + django_deleted
            logger.info(f"Invalidated {total_deleted} total keys for user: {user_id}")
            return total_deleted > 0

        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {str(e)}")
            return False

    def invalidate_group_cache(self, group_id: int) -> bool:
        """
        Invalidate all cache entries for a specific group using Redis SCAN.

        Args:
            group_id: Group ID to invalidate cache for

        Returns:
            True if successful, False otherwise
        """
        try:
            pattern = f"{self.cache_prefix}:*:group_{group_id}:*"
            deleted_count = 0

            if self.redis_client:
                # Use Redis SCAN to find and delete matching keys
                try:
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            deleted_count += self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                    logger.info(f"Invalidated {deleted_count} Redis keys for group: {group_id}")
                except RedisError as e:
                    logger.error(f"Redis invalidation failed: {e}")
                    return False

            django_deleted = 0
            keys_to_remove = set()
            for key in self.key_tracker.copy():
                if f"group_{group_id}" in key:
                    try:
                        cache.delete(key)
                        keys_to_remove.add(key)
                        django_deleted += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete Django cache key {key}: {e}")

            self.key_tracker -= keys_to_remove

            total_deleted = deleted_count + django_deleted
            logger.info(f"Invalidated {total_deleted} total keys for group: {group_id}")
            return total_deleted > 0

        except Exception as e:
            logger.error(f"Error invalidating cache for group {group_id}: {str(e)}")
            return False

    def clear_all_recommendations(self) -> bool:
        """
        Clear all recommendation cache entries using Redis pattern matching.

        Returns:
            True if successful, False otherwise
        """
        try:
            pattern = f"{self.cache_prefix}:*"
            deleted_count = 0

            if self.redis_client:
                try:
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            deleted_count += self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                    logger.info(f"Cleared {deleted_count} Redis recommendation keys")
                except RedisError as e:
                    logger.error(f"Redis clear failed: {e}")
                    return False

            django_deleted = 0
            for key in self.key_tracker.copy():
                try:
                    cache.delete(key)
                    django_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete Django cache key {key}: {e}")

            self.key_tracker.clear()

            total_deleted = deleted_count + django_deleted
            logger.info(f"Cleared {total_deleted} total recommendation cache entries")
            return total_deleted > 0

        except Exception as e:
            logger.error(f"Error clearing recommendation cache: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics including Redis metrics.

        Returns:
            Dictionary with detailed cache statistics
        """
        try:
            stats = {
                'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
                'default_timeout': self.default_timeout,
                'user_timeout': self.user_timeout,
                'tracked_keys_count': len(self.key_tracker),
                'redis_available': self.redis_client is not None
            }

            if self.redis_client:
                try:
                    redis_info = self.redis_client.info()
                    stats.update({
                        'redis_used_memory': redis_info.get('used_memory_human', 'N/A'),
                        'redis_connected_clients': redis_info.get('connected_clients', 0),
                        'redis_total_commands_processed': redis_info.get('total_commands_processed', 0),
                        'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                        'redis_keyspace_misses': redis_info.get('keyspace_misses', 0),
                    })

                    hits = redis_info.get('keyspace_hits', 0)
                    misses = redis_info.get('keyspace_misses', 0)
                    if hits + misses > 0:
                        stats['redis_hit_rate'] = round(hits / (hits + misses) * 100, 2)
                    else:
                        stats['redis_hit_rate'] = 0

                    pattern = f"{self.cache_prefix}:*"
                    cursor = 0
                    total_keys = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        total_keys += len(keys)
                        if cursor == 0:
                            break
                    stats['redis_recommendation_keys'] = total_keys

                except RedisError as e:
                    logger.warning(f"Failed to get Redis stats: {e}")
                    stats['redis_error'] = str(e)

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {'error': str(e)}

    def _generate_cache_key(
        self,
        user_id: Optional[str],
        group_id: Optional[int],
        limit: int
    ) -> str:
        """Generate cache key for recommendations."""

        key_parts = [self.cache_prefix]

        if user_id:
            key_parts.append(f"user_{user_id}")
        if group_id:
            key_parts.append(f"group_{group_id}")

        key_parts.append(f"limit_{limit}")

        return ":".join(key_parts)


cache_service = RecommendationCacheService()
