from django.urls import path
from .views import (
    PostListView,
    PostCreateView,
    PostDetailView,
    PostReplyCreateView,
    PostLikeToggleView,
)

urlpatterns = [
    path("", PostListView.as_view(), name="post-list"),
    path("create/", PostCreateView.as_view(), name="post-create"),
    path("<int:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("<int:pk>/like/", PostLikeToggleView.as_view(), name="post-like"),
    path("<int:post_id>/reply/", PostReplyCreateView.as_view(), name="post-reply"),
]
