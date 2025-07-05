import jwt
from django.conf import settings
from django.http import JsonResponse

class JWTDecodeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token_parts = auth_header.split(' ')
            if len(token_parts) != 2:
                return JsonResponse({'error': 'Missing or invalid Authorization headers'}, status=401)

            token = token_parts[1].strip()
            if not token:
                return JsonResponse({'error': 'Missing or invalid Authorization headers'}, status=401)

            try:
                payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=['RS256'])
                request.user_id = payload.get('sub')
            except jwt.InvalidTokenError:
                return JsonResponse({'error': "Invalid JWT"}, status=401)
        elif auth_header and not auth_header.startswith('Bearer '):
            # Malformed authorization header
            return JsonResponse({'error': 'Missing or invalid Authorization headers'}, status=401)
        else:
            # No authorization header - for testing and development, we'll allow this
            # but set user_id to None
            request.user_id = None

        response = self.get_response(request)
        return response



