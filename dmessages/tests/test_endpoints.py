import json
import jwt
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from ..models import Message


class MessagesEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.messages_url = '/messages/'
        self.test_user_id = 'user123'
        self.recipient_user_id = 'user456'

        # Create test messages
        self.message1 = Message.objects.create(
            sender_id='sender1',
            recipient_id=self.test_user_id,
            content='First message to user123'
        )
        self.message2 = Message.objects.create(
            sender_id='sender2',
            recipient_id=self.test_user_id,
            content='Second message to user123'
        )
        self.message3 = Message.objects.create(
            sender_id=self.test_user_id,
            recipient_id='other_user',
            content='Message sent by user123'
        )

        # Mock JWT payload
        self.mock_jwt_payload = {
            'sub': self.test_user_id,
            'exp': 9999999999
        }

        self.valid_message_data = {
            'recipient_id': self.recipient_user_id,
            'content': 'Hello, this is a test message!'
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

    # GET /messages/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_get_messages_with_valid_jwt(self, mock_jwt_decode):
        """Test GET /messages/ with valid JWT token."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only messages for user123 as recipient

    @patch('tweets.middleware.jwt.decode')
    def test_get_messages_recipient_filtering(self, mock_jwt_decode):
        """Test GET /messages/ returns only messages for authenticated user as recipient."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # All returned messages should have user123 as recipient
        for message in response.data:
            self.assertEqual(message['recipient_id'], self.test_user_id)

        # Should not include message sent BY user123
        message_contents = [msg['content'] for msg in response.data]
        self.assertNotIn('Message sent by user123', message_contents)

    @patch('tweets.middleware.jwt.decode')
    def test_get_messages_different_user(self, mock_jwt_decode):
        """Test GET /messages/ with different user returns their messages only."""
        mock_jwt_payload = {'sub': 'other_user'}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers('other_user')
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only message to other_user
        self.assertEqual(response.data[0]['content'], 'Message sent by user123')

    def test_get_messages_without_jwt(self):
        """Test GET /messages/ without JWT token returns 401."""
        response = self.client.get(self.messages_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('tweets.middleware.jwt.decode')
    def test_get_messages_with_invalid_jwt(self, mock_jwt_decode):
        """Test GET /messages/ with invalid JWT token returns 401."""
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('tweets.middleware.jwt.decode')
    def test_get_messages_empty_for_user(self, mock_jwt_decode):
        """Test GET /messages/ returns empty list for user with no messages."""
        mock_jwt_payload = {'sub': 'user_no_messages'}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers('user_no_messages')
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @patch('tweets.middleware.jwt.decode')
    def test_get_messages_response_format(self, mock_jwt_decode):
        """Test GET /messages/ returns proper response format."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        message_data = response.data[0]
        expected_fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        for field in expected_fields:
            self.assertIn(field, message_data)

    # POST /messages/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_post_message_with_valid_jwt(self, mock_jwt_decode):
        """Test POST /messages/ with valid JWT token creates message."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 4)  # 3 existing + 1 new

        created_message = Message.objects.get(content='Hello, this is a test message!')
        self.assertEqual(created_message.sender_id, self.test_user_id)
        self.assertEqual(created_message.recipient_id, self.recipient_user_id)

    def test_post_message_without_jwt(self):
        """Test POST /messages/ without JWT token returns 401."""
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Message.objects.count(), 3)  # No new messages created

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_with_invalid_jwt(self, mock_jwt_decode):
        """Test POST /messages/ with invalid JWT token returns 401."""
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Invalid token")

        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Message.objects.count(), 3)

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_invalid_data(self, mock_jwt_decode):
        """Test POST /messages/ with invalid data returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'recipient_id': '', 'content': ''}
        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)
        self.assertIn('content', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_missing_content(self, mock_jwt_decode):
        """Test POST /messages/ with missing content returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'recipient_id': 'user456'}
        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_missing_recipient(self, mock_jwt_decode):
        """Test POST /messages/ with missing recipient_id returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'content': 'Test message'}
        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_response_format(self, mock_jwt_decode):
        """Test POST /messages/ returns proper response format."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

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

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_sender_id_from_jwt(self, mock_jwt_decode):
        """Test POST /messages/ assigns sender_id from JWT token."""
        test_user_id = 'jwt_user_789'
        mock_jwt_payload = {'sub': test_user_id}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers(test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sender_id'], test_user_id)

    @patch('tweets.middleware.jwt.decode')
    def test_post_message_ignores_sender_id_in_data(self, mock_jwt_decode):
        """Test POST /messages/ ignores sender_id in request data, uses JWT."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        data_with_sender_id = self.valid_message_data.copy()
        data_with_sender_id['sender_id'] = 'hacker_user'

        response = self.client.post(
            self.messages_url,
            data=json.dumps(data_with_sender_id),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sender_id'], self.test_user_id)  # From JWT
        self.assertNotEqual(response.data['sender_id'], 'hacker_user')

    @patch('tweets.middleware.jwt.decode')
    def test_post_self_message(self, mock_jwt_decode):
        """Test POST /messages/ allows sending message to self."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        self_message_data = {
            'recipient_id': self.test_user_id,
            'content': 'Note to self'
        }

        response = self.client.post(
            self.messages_url,
            data=json.dumps(self_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sender_id'], response.data['recipient_id'])

    @patch('tweets.middleware.jwt.decode')
    def test_post_long_content(self, mock_jwt_decode):
        """Test POST /messages/ with very long content."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        long_content = 'This is a very long message. ' * 100
        long_message_data = {
            'recipient_id': 'user456',
            'content': long_content
        }

        response = self.client.post(
            self.messages_url,
            data=json.dumps(long_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['content']), len(long_content))

    @patch('tweets.middleware.jwt.decode')
    def test_post_special_characters(self, mock_jwt_decode):
        """Test POST /messages/ with special characters."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        special_content = 'Hello! 🌟 This has émojis and spécial chars: @#$%^&*()'
        special_message_data = {
            'recipient_id': 'user456',
            'content': special_content
        }

        response = self.client.post(
            self.messages_url,
            data=json.dumps(special_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], special_content)

    @patch('tweets.middleware.jwt.decode')
    def test_recipient_id_too_long(self, mock_jwt_decode):
        """Test POST /messages/ with recipient_id exceeding max length."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {
            'recipient_id': 'x' * 101,
            'content': 'Test message'
        }

        response = self.client.post(
            self.messages_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)

    # HTTP Method validation tests
    @patch('tweets.middleware.jwt.decode')
    def test_unsupported_http_methods(self, mock_jwt_decode):
        """Test unsupported HTTP methods return 405."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

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

    # Content type handling tests
    @patch('tweets.middleware.jwt.decode')
    def test_content_type_handling(self, mock_jwt_decode):
        """Test different content types are handled properly."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        # Test form data
        response = self.client.post(
            self.messages_url,
            data=self.valid_message_data,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test JSON data
        response = self.client.post(
            self.messages_url,
            data=json.dumps(self.valid_message_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Message ordering tests
    @patch('tweets.middleware.jwt.decode')
    def test_message_ordering(self, mock_jwt_decode):
        """Test messages are returned in consistent order."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.messages_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Verify consistent ordering (by creation order or timestamp)
        message_ids = [msg['id'] for msg in response.data]
        self.assertIn(self.message1.id, message_ids)
        self.assertIn(self.message2.id, message_ids)