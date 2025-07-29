import json
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from chirp.jwt_utils import generate_test_token
from ..models import Message
import unittest


@unittest.skip("JWT authentication disabled for development")
class MessagesEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.messages_url = '/messages/'
        self.test_user_id = 'user123'
        self.test_user_id_2 = 'user456'
        self.valid_message_data = {
            'recipient_id': self.test_user_id_2,
            'content': 'Hello, this is a test message!'
        }

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_messages_with_valid_jwt(self):
        """Test GET /messages/ with valid JWT token."""
        # Create messages where user123 is the recipient
        Message.objects.create(
            sender_id='sender1',
            recipient_id=self.test_user_id,
            content='Message 1'
        )
        Message.objects.create(
            sender_id='sender2',
            recipient_id=self.test_user_id,
            content='Message 2'
        )

        # Create a message where user123 is NOT the recipient (should be filtered out)
        Message.objects.create(
            sender_id='sender3',
            recipient_id='other_user',
            content='Message 3'
        )

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only messages for user123

    def test_get_messages_without_jwt(self):
        """Test GET /messages/ without JWT token returns 401."""
        response = self.client.get(self.messages_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_get_messages_with_invalid_jwt(self):
        """Test GET /messages/ with invalid JWT token returns 401."""
        response = self.client.get(
            self.messages_url,
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.json())

    def test_get_messages_filters_by_recipient(self):
        """Test GET /messages/ only returns messages for authenticated user."""
        # Create messages for different recipients
        Message.objects.create(
            sender_id='sender1',
            recipient_id=self.test_user_id,
            content='Message for user123'
        )
        Message.objects.create(
            sender_id='sender2',
            recipient_id=self.test_user_id_2,
            content='Message for user456'
        )

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Message for user123')

    def test_get_messages_empty_database(self):
        """Test GET /messages/ with empty database returns empty list."""
        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_messages_response_format(self):
        """Test GET /messages/ returns proper response format."""
        message = Message.objects.create(
            sender_id='sender1',
            recipient_id=self.test_user_id,
            content='Test message'
        )

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        message_data = response.data[0]
        expected_fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        for field in expected_fields:
            self.assertIn(field, message_data)

    def test_post_message_with_valid_jwt(self):
        """Test POST /messages/ with valid JWT token creates message."""
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)

        created_message = Message.objects.first()
        self.assertEqual(created_message.content, 'Hello, this is a test message!')
        self.assertEqual(created_message.sender_id, self.test_user_id)
        self.assertEqual(created_message.recipient_id, self.test_user_id_2)

    def test_post_message_without_jwt(self):
        """Test POST /messages/ without JWT token returns 401."""
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Message.objects.count(), 0)

    def test_post_message_with_invalid_jwt(self):
        """Test POST /messages/ with invalid JWT token returns 401."""
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Message.objects.count(), 0)

    def test_post_message_invalid_data(self):
        """Test POST /messages/ with invalid data returns 400."""
        invalid_data = {'content': ''}  # Empty content
        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)
        self.assertEqual(Message.objects.count(), 0)

    def test_post_message_missing_recipient(self):
        """Test POST /messages/ with missing recipient returns 400."""
        invalid_data = {'content': 'Hello'}
        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)
        self.assertEqual(Message.objects.count(), 0)

    def test_post_message_empty_recipient(self):
        """Test POST /messages/ with empty recipient returns 400."""
        invalid_data = {'recipient_id': '', 'content': 'Hello'}
        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)
        self.assertEqual(Message.objects.count(), 0)

    def test_post_message_response_format(self):
        """Test POST /messages/ returns proper response format."""
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_post_message_sender_id_from_jwt(self):
        """Test POST /messages/ assigns sender_id from JWT token."""
        test_user_id = 'jwt_user_456'

        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers(test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sender_id'], test_user_id)

    def test_post_message_ignores_sender_id_in_data(self):
        """Test POST /messages/ ignores sender_id in request data, uses JWT."""
        data_with_sender_id = self.valid_message_data.copy()
        data_with_sender_id['sender_id'] = 'should_be_ignored'

        response = self.client.post(
            self.messages_url,
            data=json.dumps(data_with_sender_id),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Should use JWT user_id, not the one in data
        self.assertEqual(response.data['sender_id'], self.test_user_id)
        self.assertNotEqual(response.data['sender_id'], 'should_be_ignored')

    def test_post_message_whitespace_content(self):
        """Test POST /messages/ allows whitespace-only content."""
        whitespace_data = {
            'recipient_id': self.test_user_id_2,
            'content': '   \n\t  '  # Only whitespace
        }
        response = self.client.post(
            self.messages_url,
            data=json.dumps(whitespace_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], '   \n\t  ')

    def test_unsupported_http_methods(self):
        """Test that unsupported HTTP methods return 405."""
        # Test PUT
        response = self.client.put(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE
        response = self.client.delete(
            self.messages_url,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_content_type_handling(self):
        """Test different content types are handled properly."""
        # Test with form data (should work)
        response = self.client.post(
            self.messages_url,
            data=self.valid_message_data,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test with JSON (should also work)
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_message_privacy(self):
        """Test that users can only see messages addressed to them."""
        # Create messages for different users
        Message.objects.create(
            sender_id='sender1',
            recipient_id=self.test_user_id,
            content='Message for user123'
        )
        Message.objects.create(
            sender_id='sender2',
            recipient_id=self.test_user_id_2,
            content='Message for user456'
        )

        # Test user123 can only see their messages
        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers(self.test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Message for user123')

        # Test user456 can only see their messages
        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Message for user456')