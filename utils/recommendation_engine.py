"""
Post Recommendation Engine

This module provides a comprehensive post recommendation system that:
- Prioritizes recent posts with high engagement
- Handles edge cases (few posts, old posts)
- Provides feed variety through smart randomization
- Scales efficiently with caching and optimization
"""

import random
import logging
from datetime import timedelta
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.db.models import QuerySet, Q
from django.core.cache import cache

from posts.models import Post
from groups.models import Group

logger = logging.getLogger(__name__)


class PostRecommendationEngine:
    """
    Main recommendation engine for posts.

    Implements time-weighted popularity scoring with smart randomization
    to provide engaging and varied content feeds.
    """


    RECENT_HOURS = 24
    FALLBACK_DAYS_7 = 7
    FALLBACK_DAYS_30 = 30
    MIN_POSTS_THRESHOLD = 5
    TOP_PERCENTAGE = 0.3
    CACHE_TIMEOUT = 300
    MAX_RECOMMENDATIONS = 50

    def __init__(self):
        self.cache_prefix = "recommendations"

    def get_recommended_posts(
        self,
        user_id: Optional[str] = None,
        group_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Post]:
        """
        Get recommended posts for a user.

        Args:
            user_id: User ID for personalized recommendations
            group_id: Specific group to filter posts
            limit: Maximum number of posts to return

        Returns:
            List of recommended Post objects
        """
        try:

            cache_key = self._generate_cache_key(user_id, group_id, limit)


            cached_posts = cache.get(cache_key)
            if cached_posts:
                logger.debug(f"Cache hit for recommendations: {cache_key}")
                return cached_posts


            posts = self._generate_recommendations(user_id, group_id, limit)


            cache.set(cache_key, posts, self.CACHE_TIMEOUT)
            logger.debug(f"Cached recommendations: {cache_key}")

            return posts

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return self._get_fallback_posts(group_id, limit)

    def _generate_recommendations(
        self,
        user_id: Optional[str],
        group_id: Optional[int],
        limit: int
    ) -> List[Post]:
        """Generate fresh recommendations based on current data."""


        posts_queryset = self._get_base_queryset(user_id, group_id)


        posts = self._get_posts_with_fallback(posts_queryset, limit)

        if not posts:
            logger.warning("No posts found for recommendations")
            return []

        scored_posts = self._calculate_popularity_scores(posts)

        recommended_posts = self._apply_smart_randomization(scored_posts, limit)

        return recommended_posts

    def _get_base_queryset(self, user_id: Optional[str], group_id: Optional[int]) -> QuerySet:
        """Get base queryset with proper filtering and optimization."""

        if group_id:
            # Single group posts
            return Post._default_manager.filter(group_id=group_id).select_related(
                'group'
            ).prefetch_related('attachments')

        if user_id:
            # User's accessible groups
            accessible_groups = Group._default_manager.filter(
                Q(is_private=False) |
                Q(members__contains=[user_id]) |
                Q(moderators__contains=[user_id]) |
                Q(creator_id=user_id)
            )
            return Post._default_manager.filter(group__in=accessible_groups).select_related(
                'group'
            ).prefetch_related('attachments')


        return Post._default_manager.filter(group__is_private=False).select_related(
            'group'
        ).prefetch_related('attachments')

    def _get_posts_with_fallback(self, queryset: QuerySet, limit: int) -> List[Post]:
        """Get posts with time-based fallback strategy."""

        # Try recent posts first (24 hours)
        recent_posts = list(queryset.filter(
            created_at__gte=timezone.now() - timedelta(hours=self.RECENT_HOURS)
        ).order_by('-created_at')[:self.MAX_RECOMMENDATIONS])

        if len(recent_posts) >= self.MIN_POSTS_THRESHOLD:
            return recent_posts

        # Fallback to 7 days
        logger.info("Insufficient recent posts, expanding to 7 days")
        week_posts = list(queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=self.FALLBACK_DAYS_7)
        ).order_by('-created_at')[:self.MAX_RECOMMENDATIONS])
        if len(week_posts) >= self.MIN_POSTS_THRESHOLD:
            return week_posts

        # Fallback to 30 days
        logger.info("Insufficient week posts, expanding to 30 days")
        month_posts = list(queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=self.FALLBACK_DAYS_30)
        ).order_by('-created_at')[:self.MAX_RECOMMENDATIONS])

        if len(month_posts) >= self.MIN_POSTS_THRESHOLD:
            return month_posts

        # Final fallback: all posts with evergreen scoring
        logger.info("Using evergreen scoring for all posts")
        return list(queryset.order_by('-created_at')[:self.MAX_RECOMMENDATIONS])

    def _calculate_popularity_scores(self, posts: List[Post]) -> List[Post]:
        """Calculate popularity scores for posts."""
        for post in posts:
            setattr(post, 'popularity_score', self._calculate_post_score(post))

        return posts

    def _calculate_post_score(self, post: Post) -> float:
        """Calculate popularity score for a single post."""
        days_ago = (timezone.now() - post.created_at).days

        if days_ago > self.FALLBACK_DAYS_30:
            return self._calculate_evergreen_score(post)

        return self._calculate_recent_score(post)

    def _calculate_recent_score(self, post: Post) -> float:
        """Calculate score for recent posts (within 30 days)."""

        hours_ago = (timezone.now() - post.created_at).total_seconds() / 3600
        time_decay = max(0.1, 1 - (hours_ago / self.RECENT_HOURS))


        like_score = post.like_count * 10
        comment_score = post.comments.count() * 3


        total_score = (like_score + comment_score) * time_decay

        return total_score

    def _calculate_evergreen_score(self, post: Post) -> float:
        """Calculate score for older posts (evergreen content)."""


        engagement_score = (post.like_count * 2) + (post.comments.count() * 1)


        days_ago = (timezone.now() - post.created_at).days
        time_factor = max(0.1, 1 / (1 + days_ago * 0.01))


        quality_bonus = 0
        if post.comments.count() > 10:
            quality_bonus += 5
        if post.like_count > 50:
            quality_bonus += 10

        return (engagement_score + quality_bonus) * time_factor

    def _apply_smart_randomization(self, posts: List[Post], limit: int) -> List[Post]:
        """Apply smart randomization for feed variety."""

        if not posts:
            return []


        sorted_posts = sorted(posts, key=lambda x: x.popularity_score, reverse=True)


        top_count = max(1, int(len(sorted_posts) * self.TOP_PERCENTAGE))
        guaranteed_top = sorted_posts[:top_count]


        remaining_posts = sorted_posts[top_count:]
        random_sample = random.sample(
            remaining_posts,
            min(len(remaining_posts), limit - top_count)
        )


        final_posts = guaranteed_top + random_sample
        random.shuffle(final_posts)

        return final_posts[:limit]

    def _get_fallback_posts(self, group_id: Optional[int], limit: int) -> List[Post]:
        """Get fallback posts when recommendation generation fails."""

        try:
            if group_id:
                return list(Post.objects.filter(group_id=group_id).order_by('-created_at')[:limit])
            return list(Post.objects.filter(group__is_private=False).order_by('-created_at')[:limit])
        except Exception as e:
            logger.error(f"Error in fallback posts: {str(e)}")
            return []

    def _generate_cache_key(self, user_id: Optional[str], group_id: Optional[int], limit: int) -> str:
        """Generate cache key for recommendations."""

        key_parts = [self.cache_prefix]

        if user_id:
            key_parts.append(f"user_{user_id}")
        if group_id:
            key_parts.append(f"group_{group_id}")

        key_parts.append(f"limit_{limit}")

        return ":".join(key_parts)

    def invalidate_user_cache(self, user_id: str):
        """Invalidate cache for a specific user."""

        try:
            cache_pattern = f"{self.cache_prefix}:user_{user_id}:*"



            logger.info(f"Cache invalidation requested for user: {user_id}")

        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {str(e)}")

    def get_recommendation_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics about the recommendation system."""

        try:
            posts_queryset = self._get_base_queryset(user_id, None)

            total_posts = posts_queryset.count()
            recent_posts = posts_queryset.filter(
                created_at__gte=timezone.now() - timedelta(hours=self.RECENT_HOURS)
            ).count()

            return {
                'total_posts': total_posts,
                'recent_posts_24h': recent_posts,
                'cache_timeout': self.CACHE_TIMEOUT,
                'max_recommendations': self.MAX_RECOMMENDATIONS
            }

        except Exception as e:
            logger.error(f"Error getting recommendation metrics: {str(e)}")
            return {}


def get_recommended_posts(
    user_id: Optional[str] = None,
    group_id: Optional[int] = None,
    limit: int = 20
) -> List[Post]:
    """
    Args:
        user_id: User ID for personalized recommendations
        group_id: Specific group to filter posts
        limit: Maximum number of posts to return

    Returns:
        List of recommended Post objects
    """
    engine = PostRecommendationEngine()
    return engine.get_recommended_posts(user_id, group_id, limit)
