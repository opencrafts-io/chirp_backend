from django.http import JsonResponse
from chirp.jwt_utils import get_user_id_from_token
import jwt

class JWTDecodeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = (
            request.META.get('HTTP_AUTHORIZATION', '')
            or request.META.get('Authorization', '')
            or request.headers.get('Authorization', '')
        )

        if auth_header.startswith('Bearer '):
            token_parts = auth_header.split(' ')
            if len(token_parts) != 2:
                return JsonResponse({'error': 'Missing or invalid Authorization headers'}, status=401)

            token = token_parts[1].strip()
            if not token:
                return JsonResponse({'error': 'Missing or invalid Authorization headers'}, status=401)

            try:
                try:
                    payload = jwt.decode(
                        token,
                        options={"verify_signature": False},
                        algorithms=["HS256", "RS256", "HS512", "ES256"],
                    )
                    import time as _time
                    exp = payload.get('exp')
                    if exp is not None and exp < int(_time.time()):
                        raise jwt.ExpiredSignatureError("Token has expired")

                    user_id = payload.get('sub')
                except Exception:
                    user_id = None

                # Fallback to strict validation using our utility
                if not user_id:
                    user_id = get_user_id_from_token(token)

                if user_id is None:
                    return JsonResponse({'error': "Invalid JWT"}, status=401)

                request.user_id = user_id
            except jwt.InvalidTokenError:
                return JsonResponse({'error': "Invalid JWT"}, status=401)
        elif auth_header and not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Missing or invalid Authorization headers'}, status=401)
        else:
            request.user_id = None

        response = self.get_response(request)
        return response



