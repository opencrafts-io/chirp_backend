from django.urls import path
from .views import (
    GroupListCreateView, GroupAddMemberView, GroupInviteView, GroupAcceptInviteView, GroupPostListCreateView
)

urlpatterns = [
    path('', GroupListCreateView.as_view(), name='group-list-create'),
    path('<int:group_id>/add-member/', GroupAddMemberView.as_view(), name='group-add-member'),
    path('<int:group_id>/invite/', GroupInviteView.as_view(), name='group-invite'),
    path('invites/<int:invite_id>/accept/', GroupAcceptInviteView.as_view(), name='group-accept-invite'),
    path('<int:group_id>/posts/', GroupPostListCreateView.as_view(), name='group-post-list-create'),
]
