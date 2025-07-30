from django.http import JsonResponse
from chirp.jwt_utils import get_user_id_from_token
import jwt

class JWTDecodeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Temporarily disabled JWT authentication
        # Set a default user_id for all requests
        request.user_id = "default_user_123"

        response = self.get_response(request)
        return response



