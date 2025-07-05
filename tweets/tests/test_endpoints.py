import json
import jwt
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from chirp.jwt_utils import generate_test_token
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

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_tweets_with_valid_jwt(self):
        """Test GET /statuses/ with valid JWT token."""
        # Create test tweets
        Tweets.objects.create(user_id='user1', content='Tweet 1')
        Tweets.objects.create(user_id='user2', content='Tweet 2')

        response = self.client.get(
            self.tweets_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_tweets_without_jwt(self):
        """Test GET /statuses/ without JWT token returns 401."""
        response = self.client.get(self.tweets_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_get_tweets_with_invalid_jwt(self):
        """Test GET /statuses/ with invalid JWT token returns 401."""
        response = self.client.get(
            self.tweets_url,
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.json())

    def test_get_tweets_with_malformed_auth_header(self):
        """Test GET /statuses/ with malformed Authorization header."""
        response = self.client.get(
            self.tweets_url,
            HTTP_AUTHORIZATION='InvalidHeader'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_tweets_empty_database(self):
        """Test GET /statuses/ with empty database returns empty list."""
        response = self.client.get(
            self.tweets_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_tweets_response_format(self):
        """Test GET /statuses/ returns proper response format."""
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

    def test_post_tweet_with_valid_jwt(self):
        """Test POST /statuses/ with valid JWT token creates tweet."""
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

    def test_post_tweet_with_invalid_jwt(self):
        """Test POST /statuses/ with invalid JWT token returns 401."""
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Tweets.objects.count(), 0)

    def test_post_tweet_invalid_data(self):
        """Test POST /statuses/ with invalid data returns 400."""
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

    def test_post_tweet_missing_content(self):
        """Test POST /statuses/ with missing content field returns 400."""
        invalid_data = {}
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_post_tweet_content_too_long(self):
        """Test POST /statuses/ with content exceeding 280 characters returns 400."""
        invalid_data = {'content': 'x' * 281}
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_post_tweet_response_format(self):
        """Test POST /statuses/ returns proper response format."""
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

    def test_post_tweet_user_id_from_jwt(self):
        """Test POST /statuses/ assigns user_id from JWT token."""
        test_user_id = 'jwt_user_456'

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers(test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_id'], test_user_id)

    def test_post_tweet_ignores_user_id_in_data(self):
        """Test POST /statuses/ ignores user_id in request data, uses JWT."""
        data_with_user_id = self.valid_tweet_data.copy()
        data_with_user_id['user_id'] = 'should_be_ignored'

        response = self.client.post(
            self.tweets_url,
            data=json.dumps(data_with_user_id),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Should use JWT user_id, not the one in data
        self.assertEqual(response.data['user_id'], self.test_user_id)
        self.assertNotEqual(response.data['user_id'], 'should_be_ignored')

    def test_unsupported_http_methods(self):
        """Test that unsupported HTTP methods return 405."""
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

    def test_content_type_handling(self):
        """Test different content types are handled properly."""
        # Test with form data (should work)
        response = self.client.post(
            self.tweets_url,
            data=self.valid_tweet_data,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test with JSON (should also work)
        response = self.client.post(
            self.tweets_url,
            data=json.dumps(self.valid_tweet_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)