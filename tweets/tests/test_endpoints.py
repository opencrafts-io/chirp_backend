import json
import jwt
from django.test import TestCase, override_settings
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from ..models import Tweets


class TweetsEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.tweets_url = '/statuses/'
        self.valid_tweet_data = {
            'content': 'This is a test tweet!'
        }
        self.test_user_id = 'user123'

        # Mock JWT token for testing
        self.mock_jwt_payload = {
            'sub': self.test_user_id,
            'exp': 9999999999  # Far future expiration
        }

    def _create_mock_jwt_token(self, user_id=None):
        """Helper method to create a mock JWT token."""
        payload = self.mock_jwt_payload.copy()
        if user_id:
            payload['sub'] = user_id
        return jwt.encode(payload, 'mock_secret', algorithm='HS256')

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers."""
        token = self._create_mock_jwt_token(user_id)
        return {'Authorization': f'Bearer {token}'}

    @patch('tweets.middleware.jwt.decode')
    def test_get_tweets_with_valid_jwt(self, mock_jwt_decode):
        """Test GET /statuses/ with valid JWT token."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        # Create test tweets
        Tweets.objects.create(user_id='user1', content='Tweet 1')
        Tweets.objects.create(user_id='user2', content='Tweet 2')

        response = self.client.get(
            self.tweets_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        mock_jwt_decode.assert_called_once()

    def test_get_tweets_without_jwt(self):
        """Test GET /statuses/ without JWT token returns 401."""
        response = self.client.get(self.tweets_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_get_tweets_with_invalid_jwt(self, mock_jwt_decode):
        """Test GET /statuses/ with invalid JWT token returns 401."""
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        response = self.client.get(
            self.tweets_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_get_tweets_with_malformed_auth_header(self):
        """Test GET /statuses/ with malformed Authorization header."""
        response = self.client.get(
            self.tweets_url,
            HTTP_AUTHORIZATION='InvalidHeader'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('tweets.middleware.jwt.decode')
    def test_get_tweets_empty_database(self, mock_jwt_decode):
        """Test GET /statuses/ with empty database returns empty list."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.tweets_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @patch('tweets.middleware.jwt.decode')
    def test_get_tweets_response_format(self, mock_jwt_decode):
        """Test GET /statuses/ returns proper response format."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        tweet = Tweets.objects.create(user_id='user123', content='Test tweet')

        response = self.client.get(
            self.tweets_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        tweet_data = response.data[0]
        expected_fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, tweet_data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_with_valid_jwt(self, mock_jwt_decode):
        """Test POST /statuses/ with valid JWT token creates tweet."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tweets.objects.count(), 1)

        created_tweet = Tweets.objects.first()
        self.assertEqual(created_tweet.content, 'This is a test tweet!')
        self.assertEqual(created_tweet.user_id, self.test_user_id)

    def test_post_tweet_without_jwt(self):
        """Test POST /statuses/ without JWT token returns 401."""
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Tweets.objects.count(), 0)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_with_invalid_jwt(self, mock_jwt_decode):
        """Test POST /statuses/ with invalid JWT token returns 401."""
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Tweets.objects.count(), 0)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_invalid_data(self, mock_jwt_decode):
        """Test POST /statuses/ with invalid data returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'content': ''}  # Empty content
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
        self.assertEqual(Tweets.objects.count(), 0)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_missing_content(self, mock_jwt_decode):
        """Test POST /statuses/ with missing content field returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {}
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_content_too_long(self, mock_jwt_decode):
        """Test POST /statuses/ with content exceeding 280 characters returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'content': 'x' * 281}
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_response_format(self, mock_jwt_decode):
        """Test POST /statuses/ returns proper response format."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_user_id_from_jwt(self, mock_jwt_decode):
        """Test POST /statuses/ assigns user_id from JWT token."""
        test_user_id = 'jwt_user_456'
        mock_jwt_payload = {'sub': test_user_id}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers(test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_id'], test_user_id)

    @patch('tweets.middleware.jwt.decode')
    def test_post_tweet_ignores_user_id_in_data(self, mock_jwt_decode):
        """Test POST /statuses/ ignores user_id in request data, uses JWT."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        data_with_user_id = self.valid_tweet_data.copy()
        data_with_user_id['user_id'] = 'hacker_user'

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(data_with_user_id),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_id'], self.test_user_id)  # From JWT
        self.assertNotEqual(response.data['user_id'], 'hacker_user')

    @patch('tweets.middleware.jwt.decode')
    def test_unsupported_http_methods(self, mock_jwt_decode):
        """Test unsupported HTTP methods return 405."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        # Test PUT
        response = self.client.put(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE
        response = self.client.delete(
            self.tweets_url,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch('tweets.middleware.jwt.decode')
    def test_content_type_handling(self, mock_jwt_decode):
        """Test different content types are handled properly."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        # Test form data
        response = self.client.post(
            self.tweets_url,
            data=self.valid_tweet_data,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test JSON data
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)