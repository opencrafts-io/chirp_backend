from rest_framework.permissions import BasePermission

from users.models import User
from .models import CommunityMembership


class IsCommunityMember(BasePermission):
    """
    Allows access only to users who are active members of the community.
    """

    def has_permission(self, request, view):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return False

        community_id = view.kwargs.get("community_id")
        return CommunityMembership.objects.filter(
            community_id=community_id, user=user, banned=False
        ).exists()


class IsCommunityModerator(BasePermission):
    """
    Allows access only to moderators or super-mods of the community.
    """

    def has_permission(self, request, view):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return False

        community_id = view.kwargs.get("community_id")
        return CommunityMembership.objects.filter(
            community_id=community_id,
            user=user,
            role__in=["moderator", "super-mod"],
            banned=False,
        ).exists()


class IsCommunitySuperMod(BasePermission):
    """
    Allows access only to super-mods of the community.
    """

    def has_permission(self, request, view):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return False

        community_id = view.kwargs.get("community_id")
        return CommunityMembership.objects.filter(
            community_id=community_id,
            user=user,
            role__in=["super-mod"],
            banned=False,
        ).exists()
