from django.urls import path
from .views import (
    PostListView,
    PostCreateView,
    PostDetailView,
    CommentCreateView,
    CommentDetailView,
    PostLikeToggleView,
    CommentLikeToggleView,
    GroupPostListView,
    RecommendationMetricsView,
    PostSearchView,
)

urlpatterns = [
    path("groups/<int:group_id>/posts/", GroupPostListView.as_view(), name="group-post-list"),
    path("groups/<int:group_id>/posts/create/", PostCreateView.as_view(), name="group-post-create"),

    path("", PostListView.as_view(), name="post-list"),
    path("create/", PostCreateView.as_view(), name="post-create"),
    path("recommendations/metrics/", RecommendationMetricsView.as_view(), name="recommendation-metrics"),
    path("search/", PostSearchView.as_view(), name="post-search"),

    path("<int:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("<int:pk>/like/", PostLikeToggleView.as_view(), name="post-like"),
    path("<int:post_id>/comments/", CommentCreateView.as_view(), name="post-comments"),
    path("<int:post_id>/comments/<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
    path("<int:post_id>/comments/<int:comment_id>/replies/", CommentCreateView.as_view(), name="comment-replies"),
    path("comments/<int:comment_id>/like/", CommentLikeToggleView.as_view(), name="comment-like"),
]
