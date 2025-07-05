import jwt
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.conf import settings
from unittest.mock import patch, Mock
from tweets.middleware import JWTDecodeMiddleware


class JWTDecodeMiddlewareTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = RequestFactory()
        self.middleware = JWTDecodeMiddleware(self.get_response)
        self.valid_payload = {
            'sub': 'user123',
            'exp': 9999999999  # Far future expiration
        }

    def get_response(self, request):
        """Mock response function for middleware."""
        return JsonResponse({'status': 'success'})

    def _create_jwt_token(self, payload, secret='test_secret', algorithm='HS256'):
        """Helper method to create JWT tokens for testing."""
        return jwt.encode(payload, secret, algorithm=algorithm)

    def test_valid_jwt_token(self):
        """Test middleware with valid JWT token."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = self.middleware(request)

        self.assertEqual(request.user_id, 'user123')
        self.assertEqual(response.status_code, 200)
        mock_decode.assert_called_once_with(token, settings.JWT_PUBLIC_KEY, algorithms=['RS256'])

    def test_missing_authorization_header(self):
        """Test middleware without Authorization header returns 401."""
        request = self.factory.get('/')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())
        self.assertIn('Missing or invalid Authorization headers', response.content.decode())

    def test_invalid_authorization_header_format(self):
        """Test middleware with invalid Authorization header format returns 401."""
        request = self.factory.get('/', HTTP_AUTHORIZATION='InvalidFormat')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())
        self.assertIn('Missing or invalid Authorization headers', response.content.decode())

    def test_authorization_header_without_bearer(self):
        """Test middleware with Authorization header not starting with Bearer returns 401."""
        request = self.factory.get('/', HTTP_AUTHORIZATION='Basic sometoken')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())

    def test_bearer_without_token(self):
        """Test middleware with Bearer but no token returns 401."""
        request = self.factory.get('/', HTTP_AUTHORIZATION='Bearer ')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())

    def test_invalid_jwt_token(self):
        """Test middleware with invalid JWT token returns 401."""
        request = self.factory.get('/', HTTP_AUTHORIZATION='Bearer invalid_token')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")
            response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())
        self.assertIn('Invalid JWT', response.content.decode())

    def test_expired_jwt_token(self):
        """Test middleware with expired JWT token returns 401."""
        expired_payload = {
            'sub': 'user123',
            'exp': 1234567890  # Past expiration
        }
        token = self._create_jwt_token(expired_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
            response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())
        self.assertIn('Invalid JWT', response.content.decode())

    def test_malformed_jwt_token(self):
        """Test middleware with malformed JWT token returns 401."""
        request = self.factory.get('/', HTTP_AUTHORIZATION='Bearer malformed.jwt.token')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.side_effect = jwt.DecodeError("Malformed token")
            response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())
        self.assertIn('Invalid JWT', response.content.decode())

    def test_jwt_without_sub_claim(self):
        """Test middleware with JWT token missing 'sub' claim."""
        payload_without_sub = {
            'exp': 9999999999,
            'iat': 1234567890
        }
        token = self._create_jwt_token(payload_without_sub)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = payload_without_sub
            response = self.middleware(request)

        # Should still work but user_id will be None
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(request.user_id)

    def test_jwt_with_empty_sub_claim(self):
        """Test middleware with JWT token having empty 'sub' claim."""
        payload_empty_sub = {
            'sub': '',
            'exp': 9999999999
        }
        token = self._create_jwt_token(payload_empty_sub)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = payload_empty_sub
            response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, '')

    def test_middleware_calls_next_on_success(self):
        """Test middleware calls next middleware/view on successful JWT validation."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        mock_get_response = Mock(return_value=JsonResponse({'test': 'response'}))
        middleware = JWTDecodeMiddleware(mock_get_response)

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = middleware(request)

        mock_get_response.assert_called_once_with(request)
        self.assertEqual(response.status_code, 200)

    def test_different_jwt_algorithms(self):
        """Test middleware handles different JWT algorithms correctly."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = self.middleware(request)

        # Verify RS256 algorithm is used
        mock_decode.assert_called_once_with(token, settings.JWT_PUBLIC_KEY, algorithms=['RS256'])

    def test_jwt_decode_uses_correct_key(self):
        """Test middleware uses correct JWT public key for verification."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = self.middleware(request)

        # Verify correct key is used
        mock_decode.assert_called_once_with(token, settings.JWT_PUBLIC_KEY, algorithms=['RS256'])

    def test_case_sensitive_bearer(self):
        """Test middleware is case sensitive for Bearer keyword."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'bearer {token}')  # lowercase

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.content.decode())

    def test_extra_spaces_in_header(self):
        """Test middleware handles extra spaces in Authorization header."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer  {token}')  # Extra space

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, 'user123')

    def test_authorization_header_with_multiple_spaces(self):
        """Test middleware handles multiple spaces in Authorization header."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer   {token}')  # Multiple spaces

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, 'user123')

    def test_response_format_on_error(self):
        """Test middleware returns proper JSON error format."""
        request = self.factory.get('/')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Content-Type'], 'application/json')

        # Parse JSON response
        import json
        response_data = json.loads(response.content.decode())
        self.assertIn('error', response_data)
        self.assertIsInstance(response_data['error'], str)

    def test_middleware_preserves_request_attributes(self):
        """Test middleware doesn't interfere with other request attributes."""
        token = self._create_jwt_token(self.valid_payload)
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        request.custom_attribute = 'test_value'

        with patch('tweets.middleware.jwt.decode') as mock_decode:
            mock_decode.return_value = self.valid_payload
            response = self.middleware(request)

        self.assertEqual(request.custom_attribute, 'test_value')
        self.assertEqual(request.user_id, 'user123')

    def test_different_user_ids(self):
        """Test middleware correctly extracts different user IDs."""
        test_cases = [
            'user123',
            'admin_user',
            'test@example.com',
            '12345',
            'special-user_123'
        ]

        for user_id in test_cases:
            with self.subTest(user_id=user_id):
                payload = {'sub': user_id, 'exp': 9999999999}
                token = self._create_jwt_token(payload)
                request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')

                with patch('tweets.middleware.jwt.decode') as mock_decode:
                    mock_decode.return_value = payload
                    response = self.middleware(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.user_id, user_id)