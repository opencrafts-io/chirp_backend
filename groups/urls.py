from django.urls import path
from .views import (
    GroupListView, GroupCreateView, GroupDetailView, GroupJoinView, GroupLeaveView,
    GroupModerationView, GroupAdminView, GroupSettingsView
)

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
]
