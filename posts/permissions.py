from rest_framework.permissions import BasePermission


class IsAuthenticatedCustom(BasePermission):
    """
    Allows access only to authenticated users.
    (i.e., request.user_id is present and not None)
    """

    def has_permission(self, request, view):
        return hasattr(request, "user_id") and request.user_id is not None