"""
Background Tasks for Post Recommendations

background tasks for maintaining the recommendation system,
including score updates, cache management, and system monitoring.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.conf import settings
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from posts.models import Post
from .recommendation_engine import PostRecommendationEngine
from .cache_service import cache_service
from .metrics_service import metrics_service

logger = logging.getLogger(__name__)


class RecommendationBackgroundTasks:
    """
   background tasks for maintaining the recommendation system.

    Handles periodic updates to popularity scores, cache management,
    system maintenance tasks, and performance monitoring.
    """

    def __init__(self):
        self.engine = PostRecommendationEngine()
        self.batch_size = getattr(settings, 'RECOMMENDATION_BATCH_SIZE', 1000)
        self.score_update_interval = getattr(settings, 'RECOMMENDATION_UPDATE_INTERVAL', 15)
        self.max_workers = getattr(settings, 'RECOMMENDATION_MAX_WORKERS', 4)
        self.performance_threshold = getattr(settings, 'RECOMMENDATION_PERFORMANCE_THRESHOLD', 1000)  # ms
        self._lock = threading.Lock()
        self._running_tasks = set()

    def update_popularity_scores(self) -> Dict[str, Any]:
        """
        Update popularity scores for recent posts with batch processing.

        Returns:
            Dictionary with update statistics
        """
        task_id = f"score_update_{int(time.time())}"

        with self._lock:
            if task_id in self._running_tasks:
                return {'error': 'Score update already running'}
            self._running_tasks.add(task_id)

        try:
            start_time = timezone.now()
            logger.info(f"Starting popularity score update: {task_id}")

            cutoff_time = timezone.now() - timedelta(days=7)
            posts_to_update = Post._default_manager.filter(
                created_at__gte=cutoff_time
            ).order_by('-created_at').values_list('id', flat=True)

            total_posts = len(posts_to_update)
            updated_count = 0
            error_count = 0

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []

                for i in range(0, total_posts, self.batch_size):
                    batch_ids = list(posts_to_update[i:i + self.batch_size])
                    future = executor.submit(self._process_score_batch, batch_ids)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        batch_result = future.result()
                        updated_count += batch_result['updated']
                        error_count += batch_result['errors']
                    except Exception as e:
                        logger.error(f"Batch processing failed: {e}")
                        error_count += 1

            self._clear_recommendation_caches()

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                'task_id': task_id,
                'total_posts_processed': total_posts,
                'posts_updated': updated_count,
                'errors': error_count,
                'duration_seconds': duration,
                'batches_processed': len(futures),
                'timestamp': end_time.isoformat()
            }

            logger.info(f"Popularity score update completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in popularity score update: {str(e)}")
            return {'error': str(e), 'task_id': task_id}
        finally:
            with self._lock:
                self._running_tasks.discard(task_id)

    def _process_score_batch(self, post_ids: List[int]) -> Dict[str, int]:
        """
        Process a batch of posts for score updates with database transactions.

        Args:
            post_ids: List of post IDs to process

        Returns:
            Dictionary with update statistics
        """
        updated = 0
        errors = 0

        try:
            with transaction.atomic():
                posts = Post._default_manager.filter(id__in=post_ids).select_for_update()

                for post in posts:
                    try:
                        new_score = self.engine._calculate_post_score(post)
                        current_score = getattr(post, 'popularity_score', 0)

                        if abs(new_score - current_score) > 0.1:
                            post.popularity_score = new_score
                            post.save(update_fields=['popularity_score'])
                            updated += 1

                    except Exception as e:
                        logger.error(f"Error updating score for post {post.id}: {str(e)}")
                        errors += 1
                        continue

        except Exception as e:
            logger.error(f"Batch transaction failed: {e}")
            errors += len(post_ids)

        return {'updated': updated, 'errors': errors}

    def refresh_trending_posts(self) -> Dict[str, Any]:
        """
        Refresh trending posts cache with parallel processing.

        Returns:
            Dictionary with refresh statistics
        """
        task_id = f"cache_refresh_{int(time.time())}"

        with self._lock:
            if task_id in self._running_tasks:
                return {'error': 'Cache refresh already running'}
            self._running_tasks.add(task_id)

        try:
            start_time = timezone.now()
            logger.info(f"Starting trending posts refresh: {task_id}")

            scenarios = [
                {'user_id': None, 'group_id': None, 'limit': 20},
                {'user_id': None, 'group_id': None, 'limit': 50},
                {'user_id': None, 'group_id': None, 'limit': 100},
            ]

            active_users = self._get_active_users()
            for user_id in active_users[:10]:  # Limit to top 10 active users
                scenarios.extend([
                    {'user_id': user_id, 'group_id': None, 'limit': 20},
                    {'user_id': user_id, 'group_id': None, 'limit': 50},
                ])

            refreshed_count = 0
            error_count = 0

            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(scenarios))) as executor:
                futures = []

                for scenario in scenarios:
                    future = executor.submit(self._refresh_scenario, scenario)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        if future.result():
                            refreshed_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        logger.error(f"Scenario refresh failed: {e}")
                        error_count += 1

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                'task_id': task_id,
                'scenarios_refreshed': refreshed_count,
                'scenarios_failed': error_count,
                'total_scenarios': len(scenarios),
                'duration_seconds': duration,
                'timestamp': end_time.isoformat()
            }

            logger.info(f"Trending posts refresh completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in trending posts refresh: {str(e)}")
            return {'error': str(e), 'task_id': task_id}
        finally:
            with self._lock:
                self._running_tasks.discard(task_id)

    def _get_active_users(self) -> List[str]:
        """Get list of active users from the last 24 hours."""
        try:
            from django.db.models import Count
            from posts.models import PostLike

            active_users = PostLike._default_manager.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).values_list('user_id', flat=True).distinct()

            return list(active_users)
        except Exception as e:
            logger.warning(f"Failed to get active users: {e}")
            return []

    def _refresh_scenario(self, scenario: Dict[str, Any]) -> bool:
        """Refresh cache for a specific scenario."""
        try:
            recommendations = self.engine.get_recommended_posts(**scenario)

            post_dicts = [self._post_to_dict(post) for post in recommendations]

            success = cache_service.set_recommendations(post_dicts, **scenario)

            if success:
                logger.debug(f"Refreshed cache for scenario: {scenario}")
            else:
                logger.warning(f"Failed to cache scenario: {scenario}")

            return success

        except Exception as e:
            logger.error(f"Error refreshing scenario {scenario}: {e}")
            return False

    def cleanup_old_metrics(self) -> Dict[str, Any]:
        """
        Clean up old metrics data with Redis pattern deletion.

        Returns:
            Dictionary with cleanup statistics
        """
        task_id = f"metrics_cleanup_{int(time.time())}"

        with self._lock:
            if task_id in self._running_tasks:
                return {'error': 'Metrics cleanup already running'}
            self._running_tasks.add(task_id)

        try:
            start_time = timezone.now()
            logger.info(f"Starting metrics cleanup: {task_id}")

            cutoff_time = timezone.now() - timedelta(days=7)
            deleted_count = 0

            try:
                metrics_prefix = "recommendation_metrics"
                old_keys = []

                recent_key = f"{metrics_prefix}:recent"
                recent_requests = cache.get(recent_key, [])

                if recent_requests:
                    filtered_requests = []
                    for req in recent_requests:
                        try:
                            req_time = datetime.fromisoformat(req['timestamp'].replace('Z', '+00:00'))
                            if req_time > cutoff_time:
                                filtered_requests.append(req)
                        except (ValueError, KeyError):
                            continue

                    cache.set(recent_key, filtered_requests, 3600)
                    deleted_count += len(recent_requests) - len(filtered_requests)
                    logger.info(f"Cleaned {deleted_count} old request metrics")

                if cache_service.redis_client:
                    pattern = f"{metrics_prefix}:request:*"
                    cursor = 0
                    while True:
                        cursor, keys = cache_service.redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            for key in keys:
                                try:
                                    ttl = cache_service.redis_client.ttl(key)
                                    if ttl > 0 and ttl < (7 * 24 * 3600):
                                        cache_service.redis_client.delete(key)
                                        deleted_count += 1
                                except Exception as e:
                                    logger.warning(f"Failed to check TTL for key {key}: {e}")
                        if cursor == 0:
                            break

            except Exception as e:
                logger.warning(f"Cache cleanup failed: {e}")

            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                'task_id': task_id,
                'cleanup_completed': True,
                'deleted_entries': deleted_count,
                'duration_seconds': duration,
                'timestamp': end_time.isoformat()
            }

            logger.info(f"Metrics cleanup completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in metrics cleanup: {str(e)}")
            return {'error': str(e), 'task_id': task_id}
        finally:
            with self._lock:
                self._running_tasks.discard(task_id)

    def get_running_tasks(self) -> List[str]:
        """Get list of currently running tasks."""
        with self._lock:
            return list(self._running_tasks)

    def is_task_running(self, task_type: str) -> bool:
        """Check if a specific type of task is currently running."""
        with self._lock:
            return any(task_type in task for task in self._running_tasks)

    def generate_system_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive system health report with  monitoring.

        Returns:
            Dictionary with system health information
        """
        try:
            start_time = timezone.now()
            logger.info("Generating system health report")

            system_metrics = metrics_service.get_system_metrics()
            performance_metrics = metrics_service.get_performance_metrics()
            content_metrics = metrics_service.get_content_metrics()
            cache_stats = cache_service.get_cache_stats()

            health_score = self._calculate_health_score(
                system_metrics, performance_metrics
            )

            status = self._determine_system_status(health_score, performance_metrics)

            running_tasks = self.get_running_tasks()

            performance_trend = self._calculate_performance_trend(performance_metrics)

            report = {
                'timestamp': timezone.now().isoformat(),
                'health_score': health_score,
                'status': status,
                'system_metrics': system_metrics,
                'performance_metrics': performance_metrics,
                'content_metrics': content_metrics,
                'cache_stats': cache_stats,
                'running_tasks': running_tasks,
                'performance_trend': performance_trend,
                'recommendations': self._get_health_recommendations(health_score, performance_metrics)
            }

            logger.info(f"System health report generated: {status} (score: {health_score})")
            return report

        except Exception as e:
            logger.error(f"Error generating system health report: {str(e)}")
            return {'error': str(e)}

    def _calculate_performance_trend(self, performance_metrics: Dict[str, Any]) -> str:
        """Calculate performance trend based on recent metrics."""
        try:
            avg_response_time = performance_metrics.get('avg_response_time_ms', 0)
            cache_hit_rate = performance_metrics.get('cache_hit_rate', 0)

            if avg_response_time < 200 and cache_hit_rate > 0.8:
                return 'excellent'
            elif avg_response_time < 500 and cache_hit_rate > 0.6:
                return 'good'
            elif avg_response_time < 1000 and cache_hit_rate > 0.4:
                return 'fair'
            else:
                return 'poor'
        except Exception:
            return 'unknown'

    def _clear_recommendation_caches(self) -> None:
        """Clear recommendation-related caches."""
        try:
            cache_service.clear_all_recommendations()
            logger.info("Recommendation caches cleared")

        except Exception as e:
            logger.error(f"Error clearing recommendation caches: {str(e)}")

    def _post_to_dict(self, post: Post) -> Dict[str, Any]:
        """Convert Post object to dictionary for caching."""
        return {
            'id': getattr(post, 'id', 0),
            'content': getattr(post, 'content', ''),
            'user_id': getattr(post, 'user_id', ''),
            'user_name': getattr(post, 'user_name', ''),
            'like_count': getattr(post, 'like_count', 0),
            'created_at': getattr(post, 'created_at', timezone.now()).isoformat(),
            'group_id': getattr(post.group, 'id', 0) if hasattr(post, 'group') and post.group else 0,
            'group_name': getattr(post.group, 'name', '') if hasattr(post, 'group') and post.group else '',
            'popularity_score': getattr(post, 'popularity_score', 0)
        }

    def _calculate_health_score(
        self,
        system_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall system health score (0-100)."""
        try:
            score = 100.0

            avg_response_time = performance_metrics.get('avg_response_time_ms', 0)
            if avg_response_time > 1000:
                score -= 30
            elif avg_response_time > 500:
                score -= 15

            cache_hit_rate = performance_metrics.get('cache_hit_rate', 0)
            if cache_hit_rate < 0.3:
                score -= 20
            elif cache_hit_rate < 0.5:
                score -= 10

            recent_posts = system_metrics.get('recent_posts_24h', 0)
            if recent_posts < 10:
                score -= 25
            elif recent_posts < 50:
                score -= 10

            return max(0, min(100, score))

        except Exception as e:
            logger.error(f"Error calculating health score: {str(e)}")
            return 50.0

    def _determine_system_status(
        self,
        health_score: float,
        performance_metrics: Dict[str, Any]
    ) -> str:
        """Determine system status based on health score and metrics."""
        if health_score >= 80:
            return 'healthy'
        elif health_score >= 60:
            return 'warning'
        elif health_score >= 40:
            return 'degraded'
        else:
            return 'critical'

    def _get_health_recommendations(
        self,
        health_score: float,
        performance_metrics: Dict[str, Any]
    ) -> List[str]:
        """Get recommendations for improving system health."""
        recommendations = []

        if health_score < 80:
            avg_response_time = performance_metrics.get('avg_response_time_ms', 0)
            if avg_response_time > 500:
                recommendations.append("Consider optimizing database queries or increasing cache timeout")

            cache_hit_rate = performance_metrics.get('cache_hit_rate', 0)
            if cache_hit_rate < 0.5:
                recommendations.append("Improve cache hit rate by adjusting cache strategies")

            if health_score < 60:
                recommendations.append("Consider scaling database or adding more caching layers")

        return recommendations


background_tasks = RecommendationBackgroundTasks()
