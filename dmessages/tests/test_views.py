from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import Mock, patch
from ..models import Message
from ..views import MessageListCreateView
from ..serializers import MessageSerializer
import unittest


@unittest.skip("JWT authentication disabled for development")
class MessageListCreateViewTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = MessageListCreateView.as_view()
        self.valid_message_data = {
            'sender_id': 'user123',
            'recipient_id': 'user456',
            'content': 'Hello, this is a test message!'
        }
        self.valid_request_data = {
            'recipient_id': 'user456',
            'content': 'Hello, this is a test message!'
        }

    def test_get_empty_messages(self):
        """Test GET request with no messages for user."""
        request = self.factory.get('/messages/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_messages_for_recipient(self):
        """Test GET request returns only messages for authenticated user as recipient."""
        # Create messages to different recipients
        Message.objects.create(
            sender_id='user789',
            recipient_id='user123',
            content='Message for user123'
        )
        Message.objects.create(
            sender_id='user456',
            recipient_id='user456',
            content='Message for user456'
        )
        Message.objects.create(
            sender_id='user789',
            recipient_id='user123',
            content='Another message for user123'
        )

        request = self.factory.get('/messages/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only messages for user123
        for message in response.data:
            self.assertEqual(message['recipient_id'], 'user123')

    def test_get_messages_filtering_logic(self):
        """Test GET request filters messages correctly by recipient_id."""
        # Create messages with different recipients
        message1 = Message.objects.create(
            sender_id='user456',
            recipient_id='user123',
            content='Message to user123'
        )
        message2 = Message.objects.create(
            sender_id='user123',
            recipient_id='user456',
            content='Message to user456'
        )

        request = self.factory.get('/messages/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], message1.id)
        self.assertEqual(response.data[0]['content'], 'Message to user123')

    def test_get_messages_serialization(self):
        """Test that GET request properly serializes messages."""
        message = Message.objects.create(**self.valid_message_data)

        request = self.factory.get('/messages/')
        request.user_id = 'user456'  # Recipient of the message

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        message_data = response.data[0]
        expected_fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        for field in expected_fields:
            self.assertIn(field, message_data)

        self.assertEqual(message_data['content'], 'Hello, this is a test message!')
        self.assertEqual(message_data['sender_id'], 'user123')
        self.assertEqual(message_data['recipient_id'], 'user456')

    def test_get_messages_multiple_conversations(self):
        """Test GET request handles multiple conversations correctly."""
        # Messages from different senders to user123
        Message.objects.create(
            sender_id='sender1',
            recipient_id='user123',
            content='Message from sender1'
        )
        Message.objects.create(
            sender_id='sender2',
            recipient_id='user123',
            content='Message from sender2'
        )
        Message.objects.create(
            sender_id='sender1',
            recipient_id='user123',
            content='Another message from sender1'
        )

        request = self.factory.get('/messages/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_post_valid_message(self):
        """Test POST request with valid data creates message."""
        request = self.factory.post('/messages/', self.valid_request_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)

        created_message = Message.objects.first()
        self.assertEqual(created_message.content, 'Hello, this is a test message!')
        self.assertEqual(created_message.sender_id, 'user123')
        self.assertEqual(created_message.recipient_id, 'user456')

    def test_post_assigns_sender_id_from_request(self):
        """Test POST request assigns sender_id from request object."""
        request = self.factory.post('/messages/', self.valid_request_data)
        request.user_id = 'authenticated_user'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sender_id'], 'authenticated_user')

    def test_post_invalid_data(self):
        """Test POST request with invalid data returns 400."""
        invalid_data = {'recipient_id': '', 'content': ''}
        request = self.factory.post('/messages/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)
        self.assertIn('content', response.data)
        self.assertEqual(Message.objects.count(), 0)

    def test_post_missing_content(self):
        """Test POST request with missing content field."""
        invalid_data = {'recipient_id': 'user456'}
        request = self.factory.post('/messages/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_post_missing_recipient_id(self):
        """Test POST request with missing recipient_id field."""
        invalid_data = {'content': 'Test message'}
        request = self.factory.post('/messages/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)

    def test_post_empty_content(self):
        """Test POST request with empty content."""
        invalid_data = {'recipient_id': 'user456', 'content': ''}
        request = self.factory.post('/messages/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_post_response_format(self):
        """Test POST request returns proper response format."""
        request = self.factory.post('/messages/', self.valid_request_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_post_data_copy_modification(self):
        """Test that POST request modifies copy of data, not original."""
        original_data = self.valid_request_data.copy()
        request = self.factory.post('/messages/', original_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Original data should not have sender_id
        self.assertNotIn('sender_id', original_data)

    def test_post_self_message(self):
        """Test user can send message to themselves."""
        self_message_data = {
            'recipient_id': 'user123',
            'content': 'Note to self'
        }
        request = self.factory.post('/messages/', self_message_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_message = Message.objects.first()
        self.assertEqual(created_message.sender_id, created_message.recipient_id)
        self.assertEqual(created_message.content, 'Note to self')

    def test_post_multiple_messages_same_conversation(self):
        """Test multiple messages can be sent in same conversation."""
        request1 = self.factory.post('/messages/', self.valid_request_data)
        request1.user_id = 'user123'

        request2_data = {
            'recipient_id': 'user456',
            'content': 'Second message'
        }
        request2 = self.factory.post('/messages/', request2_data)
        request2.user_id = 'user123'

        response1 = self.view(request1)
        response2 = self.view(request2)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 2)

    def test_post_long_content(self):
        """Test POST request with very long content."""
        long_content = 'This is a very long message. ' * 100
        long_message_data = {
            'recipient_id': 'user456',
            'content': long_content
        }
        request = self.factory.post('/messages/', long_message_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['content']), len(long_content))

    def test_post_special_characters(self):
        """Test POST request with special characters in content."""
        special_content = 'Hello! 🌟 This has émojis and spécial chars: @#$%^&*()'
        special_message_data = {
            'recipient_id': 'user456',
            'content': special_content
        }
        request = self.factory.post('/messages/', special_message_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], special_content)

    def test_view_uses_correct_serializer(self):
        """Test that view uses MessageSerializer."""
        request = self.factory.get('/messages/')
        request.user_id = 'user123'

        with patch('dmessages.views.MessageSerializer') as mock_serializer:
            mock_serializer.return_value.data = []
            response = self.view(request)
            mock_serializer.assert_called()

    def test_get_queryset_filters_correctly(self):
        """Test GET request filters messages by recipient_id only."""
        # Create messages where user123 is sender and recipient
        Message.objects.create(
            sender_id='user123',
            recipient_id='user456',
            content='Sent by user123'
        )
        Message.objects.create(
            sender_id='user456',
            recipient_id='user123',
            content='Received by user123'
        )

        request = self.factory.get('/messages/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only the received message
        self.assertEqual(response.data[0]['content'], 'Received by user123')
        self.assertEqual(response.data[0]['recipient_id'], 'user123')

    def test_post_recipient_id_too_long(self):
        """Test POST request with recipient_id exceeding max length."""
        invalid_data = {
            'recipient_id': 'x' * 101,
            'content': 'Test message'
        }
        request = self.factory.post('/messages/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)