from django.urls import path
from .views import (
    GroupListView, GroupPostableView, GroupCreateView, GroupDetailView, GroupDetailWithUserView, GroupJoinView, GroupLeaveView,
    GroupModerationView, GroupAdminView, GroupSettingsView, GroupRulesView, GroupRuleEditView,
    GroupMembersView, GroupModeratorsView, GroupBannedUsersView,
    GroupDeleteView, InviteLinkCreateView, InviteLinkJoinView, InviteLinkListView,
    GroupSearchView,
)
from posts.views import GroupPostListView, PostCreateView

urlpatterns = [
    # Community management
    path('', GroupListView.as_view(), name='group-list'),
    path('postable/', GroupPostableView.as_view(), name='group-postable'),
    path('create/', GroupCreateView.as_view(), name='group-create'),
    path('<int:group_id>/', GroupDetailView.as_view(), name='group-detail'),
    path('<int:group_id>/detail/', GroupDetailWithUserView.as_view(), name='group-detail-with-user'),
    path('<int:group_id>/join/', GroupJoinView.as_view(), name='group-join'),
    path('<int:group_id>/leave/', GroupLeaveView.as_view(), name='group-leave'),

    # Community moderation
    path('<int:group_id>/moderate/', GroupModerationView.as_view(), name='group-moderate'),
    path('<int:group_id>/admin/', GroupAdminView.as_view(), name='group-admin'),
    path('<int:group_id>/settings/', GroupModerationView.as_view(), name='group-settings'),
    path('<int:group_id>/delete/', GroupDeleteView.as_view(), name='group-delete'),

    # Invite links
    path('<int:group_id>/invite-links/', InviteLinkListView.as_view(), name='invite-links-list'),
    path('<int:group_id>/invite-links/create/', InviteLinkCreateView.as_view(), name='invite-link-create'),
    path('<int:group_id>/join/invite/<str:invite_token>/', InviteLinkJoinView.as_view(), name='invite-link-join'),

    # Community rules/guidelines
    path('<int:group_id>/rules/', GroupRulesView.as_view(), name='group-rules'),
    path('<int:group_id>/rules/<int:rule_index>/', GroupRuleEditView.as_view(), name='group-rule-edit'),

    # Community users
    path('<int:group_id>/members/', GroupMembersView.as_view(), name='group-members'),
    path('<int:group_id>/moderators/', GroupModeratorsView.as_view(), name='group-moderators'),
    path('<int:group_id>/banned/', GroupBannedUsersView.as_view(), name='group-banned'),

    # Group posts
    path('<int:group_id>/posts/', GroupPostListView.as_view(), name='group-posts'),
    path('<int:group_id>/posts/create/', PostCreateView.as_view(), name='group-post-create'),

    # Search
    path('search/', GroupSearchView.as_view(), name='group-search'),
]
