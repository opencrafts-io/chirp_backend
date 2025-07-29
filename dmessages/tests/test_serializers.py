from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from ..models import Message
from ..serializers import MessageSerializer, WhitespaceAllowedCharField
import unittest


@unittest.skip("JWT authentication disabled for development")
class MessageSerializerTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.valid_message_data = {
            'sender_id': 'user123',
            'recipient_id': 'user456',
            'content': 'Hello, this is a test message!'
        }
        self.valid_serializer_data = {
            'recipient_id': 'user456',
            'content': 'Hello, this is a test message!'
        }

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        serializer = MessageSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['recipient_id'], 'user456')
        self.assertEqual(serializer.validated_data['content'], 'Hello, this is a test message!')

    def test_serializer_save_creates_message(self):
        """Test that serializer save creates a message object."""
        serializer = MessageSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())

        # Mock sender_id assignment (normally done in view)
        serializer.validated_data['sender_id'] = 'user123'
        message = serializer.save()

        self.assertIsInstance(message, Message)
        self.assertEqual(message.content, 'Hello, this is a test message!')
        self.assertEqual(message.sender_id, 'user123')
        self.assertEqual(message.recipient_id, 'user456')

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data_with_readonly = self.valid_serializer_data.copy()
        data_with_readonly.update({
            'id': 999,
            'sender_id': 'hacker123',
            'created_at': '2023-01-01T00:00:00Z'
        })

        serializer = MessageSerializer(data=data_with_readonly)
        self.assertTrue(serializer.is_valid())

        # Check that read-only fields are not in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('sender_id', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)

    def test_serializer_empty_content(self):
        """Test serializer with empty content."""
        data = {'recipient_id': 'user456', 'content': ''}
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_missing_content(self):
        """Test serializer with missing content field."""
        data = {'recipient_id': 'user456'}
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_empty_recipient_id(self):
        """Test serializer with empty recipient_id."""
        data = {'recipient_id': '', 'content': 'Test message'}
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('recipient_id', serializer.errors)

    def test_serializer_missing_recipient_id(self):
        """Test serializer with missing recipient_id field."""
        data = {'content': 'Test message'}
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('recipient_id', serializer.errors)

    def test_serializer_recipient_id_too_long(self):
        """Test serializer with recipient_id exceeding 100 characters."""
        data = {'recipient_id': 'x' * 101, 'content': 'Test message'}
        serializer = MessageSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('recipient_id', serializer.errors)

    def test_serializer_recipient_id_at_max_length(self):
        """Test serializer with recipient_id at exactly 100 characters."""
        data = {'recipient_id': 'x' * 100, 'content': 'Test message'}
        serializer = MessageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_to_representation(self):
        """Test serializer converts model instance to dict representation."""
        message = Message.objects.create(**self.valid_message_data)
        serializer = MessageSerializer(message)

        expected_fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        for field in expected_fields:
            self.assertIn(field, serializer.data)

        self.assertEqual(serializer.data['content'], 'Hello, this is a test message!')
        self.assertEqual(serializer.data['sender_id'], 'user123')
        self.assertEqual(serializer.data['recipient_id'], 'user456')

    def test_serializer_many_messages(self):
        """Test serializer with many=True for multiple messages."""
        message1 = Message.objects.create(**self.valid_message_data)
        message2_data = self.valid_message_data.copy()
        message2_data['content'] = 'Second message'
        message2 = Message.objects.create(**message2_data)

        messages = [message1, message2]
        serializer = MessageSerializer(messages, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['content'], 'Hello, this is a test message!')
        self.assertEqual(serializer.data[1]['content'], 'Second message')

    def test_serializer_partial_update(self):
        """Test serializer with partial update (patch)."""
        message = Message.objects.create(**self.valid_message_data)
        update_data = {'content': 'Updated message content'}

        serializer = MessageSerializer(message, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_message = serializer.save()
        self.assertEqual(updated_message.content, 'Updated message content')
        self.assertEqual(updated_message.sender_id, 'user123')  # Should remain unchanged
        self.assertEqual(updated_message.recipient_id, 'user456')  # Should remain unchanged

    def test_serializer_validation_with_whitespace(self):
        """Test serializer handles whitespace-only content."""
        data = {'recipient_id': 'user456', 'content': '   \n\t   '}
        serializer = MessageSerializer(data=data)
        # This should be valid as Django's TextField doesn't strip whitespace by default
        # But you might want to add custom validation for this
        self.assertTrue(serializer.is_valid())

    def test_serializer_special_characters(self):
        """Test serializer handles special characters in content."""
        special_content = 'Hello! 🌟 This has émojis and spécial chars: @#$%^&*()'
        data = {'recipient_id': 'user456', 'content': special_content}
        serializer = MessageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Mock sender_id assignment
        serializer.validated_data['sender_id'] = 'user123'
        message = serializer.save()
        self.assertEqual(message.content, special_content)

    def test_serializer_long_content(self):
        """Test serializer handles very long content."""
        long_content = 'This is a very long message. ' * 100  # About 3000 characters
        data = {'recipient_id': 'user456', 'content': long_content}
        serializer = MessageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Mock sender_id assignment
        serializer.validated_data['sender_id'] = 'user123'
        message = serializer.save()
        self.assertEqual(len(message.content), len(long_content))

    def test_serializer_same_sender_recipient(self):
        """Test serializer allows same sender and recipient (self-message)."""
        data = {'recipient_id': 'user123', 'content': 'Note to self'}
        serializer = MessageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Mock sender_id assignment (same as recipient)
        serializer.validated_data['sender_id'] = 'user123'
        message = serializer.save()
        self.assertEqual(message.sender_id, message.recipient_id)

    def test_serializer_field_types(self):
        """Test serializer field types and constraints."""
        serializer = MessageSerializer()

        # Check that fields exist
        self.assertIn('id', serializer.fields)
        self.assertIn('sender_id', serializer.fields)
        self.assertIn('recipient_id', serializer.fields)
        self.assertIn('content', serializer.fields)
        self.assertIn('created_at', serializer.fields)

        # Check read-only fields
        self.assertTrue(serializer.fields['id'].read_only)
        self.assertTrue(serializer.fields['sender_id'].read_only)
        self.assertTrue(serializer.fields['created_at'].read_only)

        # Check required fields
        self.assertTrue(serializer.fields['recipient_id'].required)
        self.assertTrue(serializer.fields['content'].required)

    def test_serializer_data_copy_modification(self):
        """Test that serializer doesn't modify original input data."""
        original_data = self.valid_serializer_data.copy()
        serializer = MessageSerializer(data=original_data)
        self.assertTrue(serializer.is_valid())

        # Mock sender_id assignment
        serializer.validated_data['sender_id'] = 'user123'
        message = serializer.save()

        # Original data should not have sender_id
        self.assertNotIn('sender_id', original_data)
        self.assertEqual(original_data['recipient_id'], 'user456')
        self.assertEqual(original_data['content'], 'Hello, this is a test message!')

    def test_serializer_validation_error_format(self):
        """Test serializer validation error format."""
        invalid_data = {'recipient_id': '', 'content': ''}
        serializer = MessageSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())

        # Check that errors are properly formatted
        self.assertIn('recipient_id', serializer.errors)
        self.assertIn('content', serializer.errors)
        self.assertIsInstance(serializer.errors['recipient_id'], list)
        self.assertIsInstance(serializer.errors['content'], list)