"""
JWT utilities for the Chirp application.

This module provides JWT token generation and validation.
In production, this can be replaced with external JWT validation.
"""

import jwt
import time
from datetime import datetime, timedelta
from django.conf import settings


class JWTManager:
    """
    JWT Manager for token generation and validation.
    """

    def __init__(self):
        # Don't access settings immediately
        self._test_secret = None
        self._algorithm = None
        self._public_key = None

    def _get_test_secret(self):
        """Get the test secret key, with lazy loading."""
        if self._test_secret is None:
            self._test_secret = getattr(settings, 'JWT_TEST_SECRET', 'test_jwt_secret_key')
        return self._test_secret

    def _get_algorithm(self):
        """Get the JWT algorithm, with lazy loading."""
        if self._algorithm is None:
            self._algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
        return self._algorithm

    def _get_public_key(self):
        """Get the public key, with lazy loading."""
        if self._public_key is None:
            # For HS256 (symmetric), use the same secret for both signing and verification
            if self._get_algorithm() == 'HS256':
                self._public_key = self._get_test_secret()
            else:
                # For asymmetric algorithms like RS256, use the configured public key
                self._public_key = getattr(settings, 'JWT_PUBLIC_KEY', self._get_test_secret())
        return self._public_key

    def generate_token(self, user_id, expires_in_hours=24):
        """
        Generate a JWT token for testing purposes.

        Args:
            user_id (str): The user ID to include in the token
            expires_in_hours (int): Token expiration time in hours

        Returns:
            str: JWT token string
        """
        payload = {
            'sub': user_id,  # Subject (user ID)
            'iat': int(time.time()),  # Issued at
            'exp': int(time.time()) + (expires_in_hours * 3600)  # Expiration
        }

        return jwt.encode(payload, self._get_test_secret(), algorithm=self._get_algorithm())

    def validate_token(self, token):
        """
        Validate a JWT token and extract the payload.

        Args:
            token (str): JWT token string

        Returns:
            dict: Decoded JWT payload

        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            # For testing, use the test secret
            # In production, this would use your JWT provider's public key
            payload = jwt.decode(
                token,
                self._get_public_key(),
                algorithms=[self._get_algorithm()]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")

    def extract_user_id(self, token):
        """
        Extract user ID from a JWT token.

        Args:
            token (str): JWT token string

        Returns:
            str: User ID from token, or None if invalid
        """
        try:
            payload = self.validate_token(token)
            return payload.get('sub')
        except jwt.InvalidTokenError:
            return None


# Global JWT manager instance - create lazily
_jwt_manager = None

def _get_jwt_manager():
    """Get the global JWT manager instance, creating it if needed."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


# Convenience functions for easy testing
def generate_test_token(user_id, expires_in_hours=24):
    """Generate a test JWT token for the given user ID."""
    return _get_jwt_manager().generate_token(user_id, expires_in_hours)


def validate_jwt_token(token):
    """Validate a JWT token and return the payload."""
    return _get_jwt_manager().validate_token(token)


def get_user_id_from_token(token):
    """Extract user ID from JWT token."""
    return _get_jwt_manager().extract_user_id(token)