"""
Metrics Service for Post Recommendations
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg
from django.core.cache import cache

from posts.models import Post
from groups.models import Group

logger = logging.getLogger(__name__)


class RecommendationMetricsService:
    """
    Service for collecting and analyzing recommendation metrics.

    Tracks performance, usage patterns, and system health
    for the recommendation engine.
    """

    def __init__(self):
        self.metrics_prefix = "recommendation_metrics"
        self.cache_timeout = 3600

    def track_recommendation_request(
        self,
        user_id: Optional[str],
        group_id: Optional[int],
        limit: int,
        response_time: float,
        posts_count: int,
        cache_hit: bool = False
    ) -> None:
        """
        Track a recommendation request.

        Args:
            user_id: User ID making the request
            group_id: Group ID if filtering by group
            limit: Requested number of posts
            response_time: Response time in milliseconds
            posts_count: Number of posts returned
            cache_hit: Whether the request was served from cache
        """
        try:
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'user_id': user_id,
                'group_id': group_id,
                'limit': limit,
                'response_time_ms': response_time,
                'posts_count': posts_count,
                'cache_hit': cache_hit
            }

            self._store_request_metrics(metrics)

            logger.debug(f"Tracked recommendation request: {metrics}")

        except Exception as e:
            logger.error(f"Error tracking recommendation request: {str(e)}")

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get overall system metrics.

        Returns:
            Dictionary with system-wide metrics
        """
        try:
            cached_metrics = cache.get(f"{self.metrics_prefix}:system")
            if cached_metrics:
                return cached_metrics

            metrics = self._calculate_system_metrics()

            cache.set(f"{self.metrics_prefix}:system", metrics, self.cache_timeout)

            return metrics

        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}

    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific user.

        Args:
            user_id: User ID to get metrics for

        Returns:
            Dictionary with user-specific metrics
        """
        try:
            cache_key = f"{self.metrics_prefix}:user:{user_id}"
            cached_metrics = cache.get(cache_key)

            if cached_metrics:
                return cached_metrics

            metrics = self._calculate_user_metrics(user_id)

            cache.set(cache_key, metrics, self.cache_timeout)

            return metrics

        except Exception as e:
            logger.error(f"Error getting user metrics for {user_id}: {str(e)}")
            return {}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance-related metrics.

        Returns:
            Dictionary with performance metrics
        """
        try:
            recent_requests = self._get_recent_requests()

            if not recent_requests:
                return {
                    'avg_response_time_ms': 0,
                    'max_response_time_ms': 0,
                    'min_response_time_ms': 0,
                    'total_requests': 0,
                    'cache_hit_rate': 0
                }

            response_times = [req.get('response_time_ms', 0) for req in recent_requests]
            cache_hits = [req.get('cache_hit', False) for req in recent_requests]

            return {
                'avg_response_time_ms': sum(response_times) / len(response_times) if response_times else 0,
                'max_response_time_ms': max(response_times) if response_times else 0,
                'min_response_time_ms': min(response_times) if response_times else 0,
                'total_requests': len(recent_requests),
                'cache_hit_rate': sum(cache_hits) / len(cache_hits) if cache_hits else 0
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {}

    def get_content_metrics(self) -> Dict[str, Any]:
        """
        Get content-related metrics.

        Returns:
            Dictionary with content metrics
        """
        try:
            total_posts = Post._default_manager.count()
            recent_posts = Post._default_manager.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()


            posts_with_likes = Post._default_manager.filter(like_count__gt=0).count()
            avg_likes = Post._default_manager.aggregate(avg_likes=Avg('like_count'))['avg_likes'] or 0


            total_groups = Group._default_manager.count()
            active_groups = Group._default_manager.filter(
                community_posts__created_at__gte=timezone.now() - timedelta(days=7)
            ).distinct().count()

            return {
                'total_posts': total_posts,
                'recent_posts_24h': recent_posts,
                'posts_with_likes': posts_with_likes,
                'avg_likes_per_post': round(avg_likes, 2),
                'total_groups': total_groups,
                'active_groups_7d': active_groups
            }

        except Exception as e:
            logger.error(f"Error getting content metrics: {str(e)}")
            return {}

    def _store_request_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store request metrics in cache."""
        try:
            timestamp = metrics['timestamp']
            cache_key = f"{self.metrics_prefix}:request:{timestamp}"
            cache.set(cache_key, metrics, 3600)

            recent_key = f"{self.metrics_prefix}:recent"
            recent_requests = cache.get(recent_key, [])
            recent_requests.append(metrics)

            if len(recent_requests) > 1000:
                recent_requests = recent_requests[-1000:]

            cache.set(recent_key, recent_requests, 3600)

        except Exception as e:
            logger.error(f"Error storing request metrics: {str(e)}")

    def _get_recent_requests(self, hours: int = 1) -> list:
        """Get recent requests from the last N hours."""
        try:
            recent_key = f"{self.metrics_prefix}:recent"
            recent_requests = cache.get(recent_key, [])

            # Filter to last N hours
            cutoff_time = timezone.now() - timedelta(hours=hours)
            filtered_requests = [
                req for req in recent_requests
                if datetime.fromisoformat(req['timestamp'].replace('Z', '+00:00')) > cutoff_time
            ]

            return filtered_requests

        except Exception as e:
            logger.error(f"Error getting recent requests: {str(e)}")
            return []

    def _calculate_system_metrics(self) -> Dict[str, Any]:
        """Calculate system-wide metrics."""
        try:

            content_metrics = self.get_content_metrics()


            performance_metrics = self.get_performance_metrics()


            return {
                **content_metrics,
                **performance_metrics,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating system metrics: {str(e)}")
            return {}

    def _calculate_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Calculate user-specific metrics."""
        try:
            recent_requests = self._get_recent_requests(24)
            user_requests = [req for req in recent_requests if req.get('user_id') == user_id]

            if not user_requests:
                return {
                    'user_id': user_id,
                    'requests_24h': 0,
                    'avg_response_time_ms': 0,
                    'cache_hit_rate': 0
                }

            response_times = [req.get('response_time_ms', 0) for req in user_requests]
            cache_hits = [req.get('cache_hit', False) for req in user_requests]

            return {
                'user_id': user_id,
                'requests_24h': len(user_requests),
                'avg_response_time_ms': sum(response_times) / len(response_times),
                'cache_hit_rate': sum(cache_hits) / len(cache_hits) if cache_hits else 0,
                'timestamp': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating user metrics for {user_id}: {str(e)}")
            return {}


metrics_service = RecommendationMetricsService()
