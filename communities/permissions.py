from rest_framework.permissions import BasePermission

from users.models import User
from .models import CommunityMembership


class IsCommunityMember(BasePermission):
    """
    Allows access only to users who are active members of the community.
    """

    def has_permission(self, request, view):
        """
        Allow access only to active, non-banned members of the community identified in the view kwargs.
        
        Checks that the request contains a `user_id`, that the corresponding User exists, and that a CommunityMembership exists for that user and the community identified by `view.kwargs['community_id']` with `banned=False`. Returns False if `user_id` is missing or the User does not exist.
        
        Returns:
            True if the requesting user is an active, non-banned member of the community identified by `view.kwargs['community_id']`, False otherwise.
        """
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
        """
        Allow access only to active (not banned) community members with the role "moderator" or "super-mod".
        
        Parameters:
            request: The incoming request; expected to have a `user_id` attribute identifying the requester.
            view: The view being accessed; expected to expose `community_id` in `view.kwargs`.
        
        Returns:
            True if the requesting user is a non-banned moderator or super-mod of the specified community, False otherwise.
        """
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
        """
        Allow access only to users who are an active, non-banned super-mod of the requested community.
        
        Parameters:
            request: The incoming request; must have a `user_id` attribute identifying the requesting user.
            view: The view handling the request; `view.kwargs` must contain `community_id` for the target community.
        
        Returns:
            True if the requesting user is an active (not banned) super-mod of the specified community, False otherwise.
        """
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
