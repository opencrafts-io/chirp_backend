from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed
from .verisafe_jwt import verify_verisafe_jwt  # from earlier


class VerisafeAuthentication(BaseAuthentication):
    def authenticate(self, request):
        """
        Authenticate a request using a Verisafe JWT provided in the Authorization header.

        Reads the "Authorization" header (expected to start with "Bearer "), verifies the token using verify_verisafe_jwt, and on success attaches the token payload to `request.verisafe_claims` and the payload subject to `request.user_id`. Returns a placeholder AnonymousUser and `None` as the auth tuple.

        Parameters:
            request: The incoming HTTP request whose headers contain the Authorization bearer token.

        Returns:
            tuple: `(user, auth)` where `user` is an `AnonymousUser` placeholder and `auth` is `None`.

        Raises:
            AuthenticationFailed: If the Authorization header is missing or not in "Bearer <token>" format, or if token verification fails.
        """

        # Skip checks for /ping
        if request.path == "/ping":
            return None

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed(
                "Wrong token format. Expected 'Bearer token'", status.HTTP_403_FORBIDDEN
            )
        token = auth_header.split(" ")[1]

        try:
            payload = verify_verisafe_jwt(token)
            request.verisafe_claims = payload
            request.user_id = payload["sub"]
            # You can return a dummy user or create a real user model if needed
            return (AnonymousUser(), None)
        except Exception as e:
            raise AuthenticationFailed(str(e))
