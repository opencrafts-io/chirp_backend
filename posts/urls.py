from django.urls import path
from .views import PostListCreateView, PostReplyListCreateView, PostDetailView

urlpatterns = [
    path('', PostListCreateView.as_view(), name='post-list'),
    path('<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('<int:post_id>/replies/', PostReplyListCreateView.as_view(), name='post-reply-list'),
    path('<int:post_id>/reply/', PostReplyListCreateView.as_view(), name='post-reply'),
]
