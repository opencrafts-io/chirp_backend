from django.http import JsonResponse
from django.conf import settings
from chirp.verisafe_client import get_verisafe_client
from chirp.jwt_utils import get_user_id_from_token
import jwt
import sys

class VerisafeAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.verisafe_client = get_verisafe_client()
        # URLs that don't require authentication
        self.exempt_urls = [
            '/ping/',
            '/admin/',
            '/static/',
            '/media/',
            '/api/docs/',
            '/docs/',
        ]

    def __call__(self, request):
        # Check if the request path is exempt from authentication
        if self._is_exempt_url(request.path):
            response = self.get_response(request)
            return response

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        is_test = self._is_test_environment()

        # In test environments, handle authentication differently
        if is_test:
            if auth_header.startswith('Bearer '):
                # For test environments with Bearer token, validate it locally
                token = auth_header.split(' ')[1]
                user_id = get_user_id_from_token(token)
                if user_id:
                    request.user_id = user_id
                    request.user_email = f"{user_id}@example.com"
                    request.user_name = f"User {user_id}"
                    request.user_roles = ["student"]
                    request.user_permissions = ["read:post:own", "create:post:own", "read:post:any"]
                    request.is_authenticated = True
                else:
                    # Fallback to default user for test tokens
                    request.user_id = "default_user_123"
                    request.user_email = "default@example.com"
                    request.user_name = "Default User"
                    request.user_roles = ["student"]
                    request.user_permissions = ["read:post:own", "create:post:own", "read:post:any"]
                    request.is_authenticated = True
            else:
                # No Bearer token in test environment, use default
                request.user_id = "default_user_123"
                request.user_email = "default@example.com"
                request.user_name = "Default User"
                request.user_roles = ["student"]
                request.user_permissions = ["read:post:own", "create:post:own", "read:post:any"]
                request.is_authenticated = True

            response = self.get_response(request)
            return response

        # Production/development logic
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
            # Provide default authentication for DEBUG mode
            if settings.DEBUG:
                request.user_id = "default_user_123"
                request.user_email = "default@example.com"
                request.user_name = "Default User"
                request.user_roles = ["student"]
                request.user_permissions = ["read:post:own", "create:post:own", "read:post:any"]
                request.is_authenticated = True
            else:
                return JsonResponse({'error': 'Authentication required'}, status=401)

        response = self.get_response(request)
        return response

    def _is_exempt_url(self, path):
        """Check if the URL path is exempt from authentication"""
        for exempt_url in self.exempt_urls:
            if path.startswith(exempt_url):
                return True
        return False

    def _is_test_environment(self):
        """Check if we're running in a test environment"""
        return (
            'test' in sys.argv or
            'pytest' in sys.argv[0] or
            'manage.py' in sys.argv[0] and 'test' in sys.argv
        )

    def _validate_jwt_token(self, token):
        """Validate JWT token with Verisafe"""
        try:
            if settings.DEBUG or self._is_test_environment():
                user_id = get_user_id_from_token(token)
                if user_id:
                    return {
                        'user_id': user_id,
                        'email': f"{user_id}@example.com",
                        'name': f"User {user_id}",
                        'roles': ['student'],
                        'permissions': ['read:post:own', 'create:post:own', 'read:post:any']
                    }

            return self.verisafe_client.validate_jwt_token(token)

        except Exception as e:
            print(f"Token validation error: {e}")
            return None



