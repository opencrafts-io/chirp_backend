from django.urls import path
from .views import (
    GroupListCreateView, GroupAddMemberView, GroupInviteView, GroupAcceptInviteView,
    GroupPostListCreateView, GroupJoinView, GroupLeaveView, GroupDiscoverView
)

urlpatterns = [
    path('', GroupListCreateView.as_view(), name='group-list-create'),
    path('discover/', GroupDiscoverView.as_view(), name='group-discover'),
    path('<str:group_name>/join/', GroupJoinView.as_view(), name='group-join'),
    path('<str:group_name>/leave/', GroupLeaveView.as_view(), name='group-leave'),
    path('<str:group_name>/add_member/', GroupAddMemberView.as_view()),
    path('<str:group_name>/invite/', GroupInviteView.as_view(), name='group-invite'),
    path('invites/<int:invite_id>/accept/', GroupAcceptInviteView.as_view(), name='group-accept-invite'),
    path('<str:group_name>/posts/', GroupPostListCreateView.as_view(), name='group-post-list-create'),
]
