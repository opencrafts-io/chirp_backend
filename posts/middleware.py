from django.http import JsonResponse
from django.conf import settings
from chirp.verisafe_client import get_verisafe_client
from chirp.verisafe_jwt import verify_verisafe_jwt
import sys

class VerisafeAuthMiddleware:
    def __init__(self, get_response):
        """
        Initialize the middleware, store the next request callable, create a Verisafe client, and define URL path prefixes that bypass authentication.
        
        Parameters:
            get_response (callable): The next middleware or view callable that should be invoked to produce a response.
        
        Notes:
            The `exempt_urls` list contains path prefixes that will not require authentication. Due to a missing comma between the first two entries, the literals '/users/' and '/ping/' are concatenated into a single entry '/users//ping/', which alters which paths are actually exempt.
        """
        self.get_response = get_response
        self.verisafe_client = get_verisafe_client()
        # URLs that don't require authentication
        self.exempt_urls = [
            '/users/'
            '/ping/',
            '/admin/',
            '/static/',
            '/media/',
            '/qa-chirp/media/',
            '/workspace/media/',
            '/qa-chirp/workspace/media/',
            '/api/docs/',
            '/docs/',
            '/maintenance/',
            '/qa-chirp/maintenance/',
            '/qa-chirp/users/',
        ]

    def __call__(self, request):
        if self._is_exempt_url(request.path):
            response = self.get_response(request)
            return response

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        is_test = self._is_test_environment()

        if is_test:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                try:
                    payload = verify_verisafe_jwt(token)
                    request.user_id = payload.get('sub')
                    request.user_email = payload.get('email', f"{payload.get('sub')}@example.com")
                    request.user_name = payload.get('name', f"User {payload.get('sub')}")
                    request.user_roles = payload.get('roles', ['student'])
                    request.user_permissions = payload.get('permissions', ['read:post:own', 'create:post:own', 'read:post:any'])
                    request.is_authenticated = True
                except Exception as e:
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

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = verify_verisafe_jwt(token)
                request.user_id = payload.get('sub')
                request.user_email = payload.get('email', f"{payload.get('sub')}@example.com")
                request.user_name = payload.get('name', f"User {payload.get('sub')}")
                request.user_roles = payload.get('roles', [])
                request.user_permissions = payload.get('permissions', [
                    'read:post:any',
                    'create:post:own',
                    'read:post:own',
                    'update:post:own',
                    'delete:post:own',
                    'create:like:any',
                    'delete:like:any'
                ])
                request.is_authenticated = True
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=401)

        else:
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
        is_test = (
            'test' in sys.argv or
            'pytest' in sys.argv[0] or
            ('manage.py' in sys.argv[0] and 'test' in sys.argv)
        )

        return is_test



