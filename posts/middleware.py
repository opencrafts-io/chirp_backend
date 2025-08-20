from django.http import JsonResponse
from django.conf import settings
from chirp.verisafe_client import get_verisafe_client
from chirp.jwt_utils import get_user_id_from_token
import jwt

class VerisafeAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.verisafe_client = get_verisafe_client()

    def __call__(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_data = self._validate_jwt_token(token)

            if user_data:
                request.user_id = user_data.get('user_id')
                request.user_email = user_data.get('email')
                request.user_name = user_data.get('name')
                request.user_roles = user_data.get('roles', [])
                request.user_permissions = user_data.get('permissions', [])
                request.is_authenticated = True
            else:
                return JsonResponse({'error': 'Invalid or expired JWT token'}, status=401)

        else:
            if settings.DEBUG:
                request.user_id = "default_user_123"
                request.user_email = "default@example.com"
                request.user_name = "Default User"
                request.user_roles = ["student"]
                request.user_permissions = ["read:post:own", "create:post:own"]
                request.is_authenticated = True
            else:
                return JsonResponse({'error': 'Authentication required'}, status=401)

        response = self.get_response(request)
        return response

    def _validate_jwt_token(self, token):
        """Validate JWT token with Verisafe"""
        try:
            if settings.DEBUG:
                user_id = get_user_id_from_token(token)
                if user_id:
                    return {
                        'user_id': user_id,
                        'email': f"{user_id}@example.com",
                        'name': f"User {user_id}",
                        'roles': ['student'],
                        'permissions': ['read:post:own', 'create:post:own']
                    }

            return self.verisafe_client.validate_jwt_token(token)

        except Exception as e:
            print(f"Token validation error: {e}")
            return None



