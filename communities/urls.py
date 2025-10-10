from django.urls import path
from .views import (
    CommunityBanUserView,
    CommunityDestroyView,
    CommunityListView,
    CommunityPostableView,
    CommunityCreateView,
    CommunityJoinView,
    CommunityLeaveView,
    CommunityRetrieveView,
    CommunityUpdateView,
    CommunitySearchView,
    CommunityMembershipApiView,
    PersonalCommunityMembershipForCommunityApiView,
    PersonalCommunityMembershipsApiView,
)

# from posts.views import  PostCreateView

urlpatterns = [
    # Community management
    path("create/", CommunityCreateView.as_view(), name="community-create"),
    path("search/", CommunitySearchView.as_view(), name="community-search"),
    path("all", CommunityListView.as_view(), name="community-list"),
    path(
        "<int:community_id>/details",
        CommunityRetrieveView.as_view(),
        name="community-detail-view",
    ),
    path(
        "<int:community_id>/update",
        CommunityUpdateView.as_view(),
        name="community-detail-view",
    ),
    path(
        "<int:community_id>/delete",
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
        PersonalCommunityMembershipsApiView.as_view(),
        name="get-personal-memberships",
    ),
    path(
        "memberships/mine/for/<int:community_id>",
        PersonalCommunityMembershipForCommunityApiView.as_view(),
        name="get-personal-memberships-for-community",
    ),
    path("postable", CommunityPostableView.as_view(), name="community-postable"),
    # banning users
    path(
        "<int:community_id>/ban/<int:pk>/",
        CommunityBanUserView.as_view(),
        name="community-ban-user",
    ),
    # Community Join and leaving
    path(
        "<int:community_id>/join/", CommunityJoinView.as_view(), name="community-join"
    ),
    path(
        "<int:community_id>/leave/",
        CommunityLeaveView.as_view(),
        name="community-leave",
    ),
    # Search
    path("search/", CommunitySearchView.as_view(), name="community-search"),
]
