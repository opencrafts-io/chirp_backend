import unittest
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from unittest.mock import patch, MagicMock
from posts.middleware import VerisafeAuthMiddleware
from chirp.jwt_utils import generate_test_token
import jwt
import json


@unittest.skip("JWT authentication disabled for development")
class VerisafeAuthMiddlewareTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=JsonResponse({'message': 'success'}))
        self.middleware = VerisafeAuthMiddleware(self.get_response)
        self.test_user_id = 'user123'

    def test_valid_bearer_token(self):
        """Test middleware with valid Bearer token."""
        token = generate_test_token(self.test_user_id)
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, self.test_user_id)
        self.get_response.assert_called_once_with(request)

    def test_no_authorization_header(self):
        """Test middleware without Authorization header."""
        request = self.factory.get('/')

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, None)
        self.get_response.assert_called_once_with(request)

    def test_invalid_bearer_token(self):
        """Test middleware with invalid Bearer token."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid_token'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Invalid JWT')
        self.get_response.assert_not_called()

    def test_malformed_authorization_header(self):
        """Test middleware with malformed Authorization header."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'InvalidHeader'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Missing or invalid Authorization headers')
        self.get_response.assert_not_called()

    def test_bearer_with_no_token(self):
        """Test middleware with Bearer but no token."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Missing or invalid Authorization headers')
        self.get_response.assert_not_called()

    def test_bearer_with_empty_token(self):
        """Test middleware with Bearer and empty token."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer   '

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Missing or invalid Authorization headers')
        self.get_response.assert_not_called()

    def test_bearer_with_multiple_spaces(self):
        """Test middleware with Bearer token with multiple spaces."""
        token = generate_test_token(self.test_user_id)
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer   {token}   extra_text'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Missing or invalid Authorization headers')
        self.get_response.assert_not_called()

    def test_expired_token(self):
        """Test middleware with expired token."""
        # Generate a token that expires immediately
        expired_token = generate_test_token(self.test_user_id, expires_in_hours=-1)
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {expired_token}'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Invalid JWT')
        self.get_response.assert_not_called()

    def test_token_with_different_user(self):
        """Test middleware with token for different user."""
        different_user_id = 'different_user_456'
        token = generate_test_token(different_user_id)
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, different_user_id)
        self.get_response.assert_called_once_with(request)

    @patch('chirp.jwt_utils.get_user_id_from_token')
    def test_jwt_decode_exception_handling(self, mock_get_user_id):
        """Test middleware handles JWT decode exceptions properly."""
        mock_get_user_id.side_effect = jwt.InvalidTokenError("Token decode error")

        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer some_token'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Invalid JWT')
        self.get_response.assert_not_called()

    @patch('chirp.jwt_utils.get_user_id_from_token')
    def test_jwt_utility_returns_none(self, mock_get_user_id):
        """Test middleware when JWT utility returns None."""
        mock_get_user_id.return_value = None

        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer some_token'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Invalid JWT')
        self.get_response.assert_not_called()

    def test_case_insensitive_bearer(self):
        """Test middleware with different case Bearer keyword."""
        token = generate_test_token(self.test_user_id)
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'bearer {token}'

        response = self.middleware(request)

        # Should not work - Bearer is case-sensitive
        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Missing or invalid Authorization headers')
        self.get_response.assert_not_called()

    def test_basic_auth_header(self):
        """Test middleware with Basic authorization header."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Basic dXNlcjpwYXNzd29yZA=='

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Missing or invalid Authorization headers')
        self.get_response.assert_not_called()

    def test_middleware_preserves_request_attributes(self):
        """Test middleware preserves other request attributes."""
        token = generate_test_token(self.test_user_id)
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        request.custom_attr = 'custom_value'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, self.test_user_id)
        self.assertEqual(request.custom_attr, 'custom_value')

    def test_middleware_with_post_request(self):
        """Test middleware works with POST requests."""
        token = generate_test_token(self.test_user_id)
        request = self.factory.post('/', {'data': 'test'})
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_id, self.test_user_id)

    def test_middleware_response_content_type(self):
        """Test middleware error responses have correct content type."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid_token'

        response = self.middleware(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_middleware_order_independence(self):
        """Test middleware works regardless of call order."""
        token = generate_test_token(self.test_user_id)

        # First request
        request1 = self.factory.get('/')
        request1.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'

        # Second request without token
        request2 = self.factory.get('/')

        response1 = self.middleware(request1)
        response2 = self.middleware(request2)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(request1.user_id, self.test_user_id)

        self.assertEqual(response2.status_code, 200)
        self.assertEqual(request2.user_id, None)