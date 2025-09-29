from django.urls import path
from .views import (
    CommunityDestroyView,
    CommunityListView,
    CommunityPostableView,
    CommunityCreateView,
    CommunityDetailView,
    CommunityDetailWithUserView,
    CommunityJoinView,
    CommunityLeaveView,
    CommunityModerationView,
    CommunityAdminView,
    CommunityRetrieveView,
    CommunitySettingsView,
    CommunityRulesView,
    CommunityRuleEditView,
    CommunityMembersView,
    CommunityModeratorsView,
    CommunityBannedUsersView,
    CommunityDeleteView,
    CommunityUpdateView,
    InviteLinkCreateView,
    InviteLinkJoinView,
    InviteLinkListView,
    CommunitySearchView,
    CommunityMembershipApiView,
    PersonalCommunityMembershipApiView,
)

# from posts.views import  PostCreateView

urlpatterns = [
    # Community management
    path("create/", CommunityCreateView.as_view(), name="community-create"),
    path("all", CommunityListView.as_view(), name="community-list"),
    path(
        "<int:id>/details",
        CommunityRetrieveView.as_view(),
        name="community-detail-view",
    ),
    path(
        "<int:id>/update",
        CommunityUpdateView.as_view(),
        name="community-detail-view",
    ),
    path(
        "<int:id>/delete",
        CommunityDestroyView.as_view(),
        name="community-delete-view",
    ),
    # Community memberships
    path(
        "<int:community_id>/memberships",
        CommunityMembershipApiView.as_view(),
        name="get-community-memberhips",
    ),
    path(
        "memberships/mine",
        PersonalCommunityMembershipApiView.as_view(),
        name="get-personal-memberships",
    ),
    # path(
    #     "<int:community_id>/memberships",
    #     CommunityMembershipApiView.as_view(),
    #     name="get-community-memberhips",
    # ),
    # Older versions
    path("postable/", CommunityPostableView.as_view(), name="community-postable"),
    path("<int:community_id>/", CommunityDetailView.as_view(), name="community-detail"),
    path(
        "<int:community_id>/detail/",
        CommunityDetailWithUserView.as_view(),
        name="community-detail-with-user",
    ),
    path(
        "<int:community_id>/join/", CommunityJoinView.as_view(), name="community-join"
    ),
    path(
        "<int:community_id>/leave/",
        CommunityLeaveView.as_view(),
        name="community-leave",
    ),
    # Community moderation
    path(
        "<int:community_id>/moderate/",
        CommunityModerationView.as_view(),
        name="community-moderate",
    ),
    path(
        "<int:community_id>/admin/",
        CommunityAdminView.as_view(),
        name="community-admin",
    ),
    path(
        "<int:community_id>/settings/",
        CommunityModerationView.as_view(),
        name="community-settings",
    ),
    path(
        "<int:community_id>/delete/",
        CommunityDeleteView.as_view(),
        name="community-delete",
    ),
    # Invite links
    path(
        "<int:community_id>/invite-links/",
        InviteLinkListView.as_view(),
        name="invite-links-list",
    ),
    path(
        "<int:community_id>/invite-links/create/",
        InviteLinkCreateView.as_view(),
        name="invite-link-create",
    ),
    path(
        "<int:community_id>/join/invite/<str:invite_token>/",
        InviteLinkJoinView.as_view(),
        name="invite-link-join",
    ),
    # Community rules/guidelines
    path(
        "<int:community_id>/rules/",
        CommunityRulesView.as_view(),
        name="community-rules",
    ),
    path(
        "<int:community_id>/rules/<int:rule_index>/",
        CommunityRuleEditView.as_view(),
        name="community-rule-edit",
    ),
    # Community users
    path(
        "<int:community_id>/members/",
        CommunityMembersView.as_view(),
        name="community-members",
    ),
    path(
        "<int:community_id>/moderators/",
        CommunityModeratorsView.as_view(),
        name="community-moderators",
    ),
    path(
        "<int:community_id>/banned/",
        CommunityBannedUsersView.as_view(),
        name="community-banned",
    ),
    # Community posts
    # path('<int:community_id>/posts/', CommunityPostListView.as_view(), name='community-posts'),
    # path('<int:community_id>/posts/create/', PostCreateView.as_view(), name='community-post-create'),
    # Search
    path("search/", CommunitySearchView.as_view(), name="community-search"),
]
