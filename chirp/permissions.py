from rest_framework.permissions import BasePermission
from functools import wraps
from django.http import JsonResponse
from groups.models import Group


class VerisafePermission(BasePermission):
    def __init__(self, required_permission):
        self.required_permission = required_permission

    def has_permission(self, request, view):
        if not hasattr(request, 'is_authenticated') or not request.is_authenticated:
            return False

        user_permissions = getattr(request, 'user_permissions', [])
        return self.required_permission in user_permissions


class CommunityPermission(BasePermission):
    """Permission class for community-specific actions"""

    def __init__(self, required_role='member', action=None):
        self.required_role = required_role
        self.action = action

    def has_permission(self, request, view):
        if not hasattr(request, 'is_authenticated') or not request.is_authenticated:
            return False

        group_id = view.kwargs.get('group_id') or request.data.get('group_id')
        if not group_id:
            return False

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return False

        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return False

        if self.required_role == 'admin':
            return group.is_admin(user_id)
        elif self.required_role == 'moderator':
            return group.is_moderator(user_id)
        elif self.required_role == 'member':
            return group.is_member(user_id)

        return False

    def has_object_permission(self, request, view, obj):
        """Check permissions for specific objects (like posts)"""
        if not hasattr(request, 'is_authenticated') or not request.is_authenticated:
            return False

        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return False

        if hasattr(obj, 'group'):
            group = obj.group
            if self.required_role == 'admin':
                return group.is_admin(user_id)
            elif self.required_role == 'moderator':
                return group.is_moderator(user_id)
            elif self.required_role == 'member':
                return group.is_member(user_id)

        return False


def require_permission(permission):
    """Decorator for requiring specific permissions"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'is_authenticated') or not request.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)

            if permission not in getattr(request, 'user_permissions', []):
                return JsonResponse({'error': 'Insufficient permissions'}, status=403)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_community_role(role='member'):
    """Decorator for requiring specific community roles"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'is_authenticated') or not request.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)

            group_id = kwargs.get('group_id') or request.data.get('group_id')
            if not group_id:
                return JsonResponse({'error': 'Group ID required'}, status=400)

            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                return JsonResponse({'error': 'Group not found'}, status=404)

            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return JsonResponse({'error': 'User ID required'}, status=400)

            if role == 'admin':
                if not group.is_admin(user_id):
                    return JsonResponse({'error': 'Admin access required'}, status=403)
            elif role == 'moderator':
                if not group.is_moderator(user_id):
                    return JsonResponse({'error': 'Moderator access required'}, status=403)
            elif role == 'member':
                if not group.is_member(user_id):
                    return JsonResponse({'error': 'Member access required'}, status=403)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


COMMUNITY_PERMISSIONS = {
    'view': 'community:view',
    'join': 'community:join',
    'post': 'community:post',
    'comment': 'community:comment',
    'moderate': 'community:moderate',
    'admin': 'community:admin',
    'ban': 'community:ban',
    'invite': 'community:invite',
    'edit': 'community:edit',
    'delete': 'community:delete',
}

COMMUNITY_ROLES = {
    'member': ['view', 'join', 'post', 'comment'],
    'moderator': ['view', 'join', 'post', 'comment', 'moderate', 'ban', 'invite'],
    'admin': ['view', 'join', 'post', 'comment', 'moderate', 'ban', 'invite', 'edit', 'delete', 'admin'],
}
