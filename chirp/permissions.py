from rest_framework.permissions import BasePermission
from functools import wraps
from django.http import JsonResponse

class VerisafePermission(BasePermission):
    def __init__(self, required_permission):
        self.required_permission = required_permission

    def has_permission(self, request, view):
        if not hasattr(request, 'is_authenticated') or not request.is_authenticated:
            return False

        user_permissions = getattr(request, 'user_permissions', [])
        return self.required_permission in user_permissions

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
