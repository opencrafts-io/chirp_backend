from rest_framework.permissions import BasePermission


class IsAuthenticatedCustom(BasePermission):
    """
    Temporarily disabled authentication - allows all requests.
    """

    def has_permission(self, request, view):
        return True