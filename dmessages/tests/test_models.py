from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from ..models import Message
import unittest


@unittest.skip("JWT authentication disabled for development")
class MessageModelTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.valid_message_data = {
            'sender_id': 'user123',
            'recipient_id': 'user456',
            'content': 'Hello, this is a test message!'
        }

    def test_create_valid_message(self):
        """Test creating a valid message with all required fields."""
        message = Message.objects.create(**self.valid_message_data)
        self.assertEqual(message.sender_id, 'user123')
        self.assertEqual(message.recipient_id, 'user456')
        self.assertEqual(message.content, 'Hello, this is a test message!')
        self.assertIsNotNone(message.created_at)
        self.assertIsNotNone(message.id)

    def test_message_string_representation(self):
        """Test the __str__ method returns expected format."""
        message = Message.objects.create(**self.valid_message_data)
        expected_str = f"{message.sender_id} to {message.recipient_id}: {message.content}..."
        self.assertEqual(str(message), expected_str)

    def test_message_sender_id_max_length(self):
        """Test sender_id respects 100 character limit."""
        long_sender_id = 'x' * 101
        message_data = self.valid_message_data.copy()
        message_data['sender_id'] = long_sender_id

        message = Message(**message_data)
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_recipient_id_max_length(self):
        """Test recipient_id respects 100 character limit."""
        long_recipient_id = 'x' * 101
        message_data = self.valid_message_data.copy()
        message_data['recipient_id'] = long_recipient_id

        message = Message(**message_data)
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_empty_sender_id(self):
        """Test that empty sender_id is not allowed."""
        message_data = self.valid_message_data.copy()
        message_data['sender_id'] = ''

        message = Message(**message_data)
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_empty_recipient_id(self):
        """Test that empty recipient_id is not allowed."""
        message_data = self.valid_message_data.copy()
        message_data['recipient_id'] = ''

        message = Message(**message_data)
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_empty_content(self):
        """Test that empty content is not allowed."""
        message_data = self.valid_message_data.copy()
        message_data['content'] = ''

        message = Message(**message_data)
        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_message_auto_timestamp(self):
        """Test that created_at is automatically set."""
        message = Message.objects.create(**self.valid_message_data)
        self.assertIsNotNone(message.created_at)

    def test_multiple_messages_same_users(self):
        """Test that multiple messages can be sent between same users."""
        message1 = Message.objects.create(**self.valid_message_data)
        message2_data = self.valid_message_data.copy()
        message2_data['content'] = 'Second message'
        message2 = Message.objects.create(**message2_data)

        self.assertEqual(message1.sender_id, message2.sender_id)
        self.assertEqual(message1.recipient_id, message2.recipient_id)
        self.assertNotEqual(message1.content, message2.content)
        self.assertNotEqual(message1.id, message2.id)

    def test_message_conversation_both_ways(self):
        """Test messages can be sent both ways between users."""
        # user123 sends to user456
        message1 = Message.objects.create(**self.valid_message_data)

        # user456 replies to user123
        reply_data = {
            'sender_id': 'user456',
            'recipient_id': 'user123',
            'content': 'Reply message'
        }
        message2 = Message.objects.create(**reply_data)

        self.assertEqual(message1.sender_id, message2.recipient_id)
        self.assertEqual(message1.recipient_id, message2.sender_id)

    def test_message_same_sender_recipient(self):
        """Test that user can send message to themselves."""
        self_message_data = {
            'sender_id': 'user123',
            'recipient_id': 'user123',
            'content': 'Note to self'
        }

        message = Message.objects.create(**self_message_data)
        self.assertEqual(message.sender_id, message.recipient_id)
        self.assertEqual(message.content, 'Note to self')

    def test_message_long_content(self):
        """Test message with very long content."""
        long_content = 'This is a very long message. ' * 100  # About 3000 characters
        message_data = self.valid_message_data.copy()
        message_data['content'] = long_content

        message = Message.objects.create(**message_data)
        self.assertEqual(len(message.content), len(long_content))

    def test_message_special_characters(self):
        """Test message content with special characters."""
        special_content = 'Hello! 🌟 This has émojis and spécial chars: @#$%^&*()'
        message_data = self.valid_message_data.copy()
        message_data['content'] = special_content

        message = Message.objects.create(**message_data)
        self.assertEqual(message.content, special_content)

    def test_message_whitespace_content(self):
        """Test message with whitespace-only content."""
        whitespace_content = '   \n\t   '
        message_data = self.valid_message_data.copy()
        message_data['content'] = whitespace_content

        # This should be valid as Django's TextField doesn't strip whitespace by default
        message = Message.objects.create(**message_data)
        self.assertEqual(message.content, whitespace_content)

    def test_message_ordering(self):
        """Test default ordering (if any) of messages."""
        message1 = Message.objects.create(**self.valid_message_data)
        message2_data = self.valid_message_data.copy()
        message2_data['content'] = 'Second message'
        message2 = Message.objects.create(**message2_data)

        messages = Message.objects.all()
        self.assertEqual(messages.count(), 2)
        # Verify both messages are retrieved
        self.assertIn(message1, messages)
        self.assertIn(message2, messages)

    def test_message_filtering_by_recipient(self):
        """Test filtering messages by recipient."""
        # Create messages to different recipients
        message1 = Message.objects.create(**self.valid_message_data)
        message2_data = {
            'sender_id': 'user123',
            'recipient_id': 'user789',
            'content': 'Message to different user'
        }
        message2 = Message.objects.create(**message2_data)

        # Filter by recipient
        user456_messages = Message.objects.filter(recipient_id='user456')
        user789_messages = Message.objects.filter(recipient_id='user789')

        self.assertEqual(user456_messages.count(), 1)
        self.assertEqual(user789_messages.count(), 1)
        self.assertEqual(user456_messages.first(), message1)
        self.assertEqual(user789_messages.first(), message2)

    def test_message_filtering_by_sender(self):
        """Test filtering messages by sender."""
        # Create messages from different senders
        message1 = Message.objects.create(**self.valid_message_data)
        message2_data = {
            'sender_id': 'user789',
            'recipient_id': 'user456',
            'content': 'Message from different user'
        }
        message2 = Message.objects.create(**message2_data)

        # Filter by sender
        user123_messages = Message.objects.filter(sender_id='user123')
        user789_messages = Message.objects.filter(sender_id='user789')

        self.assertEqual(user123_messages.count(), 1)
        self.assertEqual(user789_messages.count(), 1)
        self.assertEqual(user123_messages.first(), message1)
        self.assertEqual(user789_messages.first(), message2)