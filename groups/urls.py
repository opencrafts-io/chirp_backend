from django.urls import path
from .views import (
    GroupListView, GroupCreateView, GroupDetailView, GroupJoinView, GroupLeaveView,
    GroupModerationView, GroupAdminView, GroupSettingsView, GroupRulesView, GroupUsersView
)
from posts.views import GroupPostListView, PostCreateView

urlpatterns = [
    # Community management
    path('', GroupListView.as_view(), name='group-list'),
    path('create/', GroupCreateView.as_view(), name='group-create'),
    path('<int:group_id>/', GroupDetailView.as_view(), name='group-detail'),
    path('<int:group_id>/join/', GroupJoinView.as_view(), name='group-join'),
    path('<int:group_id>/leave/', GroupLeaveView.as_view(), name='group-leave'),

    # Community moderation
    path('<int:group_id>/moderate/', GroupModerationView.as_view(), name='group-moderate'),
    path('<int:group_id>/admin/', GroupAdminView.as_view(), name='group-admin'),
    path('<int:group_id>/settings/', GroupSettingsView.as_view(), name='group-settings'),

    # Community rules/guidelines
    path('<int:group_id>/rules/', GroupRulesView.as_view(), name='group-rules'),

    # Community users
    path('<int:group_id>/users/', GroupUsersView.as_view(), name='group-users'),

    # Group posts
    path('<int:group_id>/posts/', GroupPostListView.as_view(), name='group-posts'),
    path('<int:group_id>/posts/create/', PostCreateView.as_view(), name='group-post-create'),
]
