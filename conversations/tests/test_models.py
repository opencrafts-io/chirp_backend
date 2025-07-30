from django.test import TestCase
from django.utils import timezone
from conversations.models import Conversation, ConversationMessage


class ConversationModelTest(TestCase):
    def setUp(self):
        self.conversation = Conversation.objects.create(
            conversation_id="conv_test123",
            participants=["user1", "user2"]
        )

    def test_conversation_creation(self):
        """Test that a conversation can be created"""
        self.assertEqual(self.conversation.conversation_id, "conv_test123")
        self.assertEqual(self.conversation.participants, ["user1", "user2"])
        self.assertIsNotNone(self.conversation.created_at)
        self.assertIsNotNone(self.conversation.updated_at)

    def test_conversation_str_representation(self):
        """Test the string representation of a conversation"""
        self.assertEqual(str(self.conversation), "Conversation conv_test123")

    def test_conversation_last_message_at_update(self):
        """Test that last_message_at can be updated when messages are added"""
        # Create a message
        message = ConversationMessage.objects.create(
            conversation=self.conversation,
            sender_id="user1",
            content="Test message"
        )

        # Manually update last_message_at (this is done in the view)
        self.conversation.last_message_at = message.created_at
        self.conversation.save()

        # Refresh conversation from database
        self.conversation.refresh_from_db()

        # last_message_at should be updated
        self.assertIsNotNone(self.conversation.last_message_at)
        self.assertEqual(self.conversation.last_message_at, message.created_at)


class ConversationMessageModelTest(TestCase):
    def setUp(self):
        self.conversation = Conversation.objects.create(
            conversation_id="conv_test123",
            participants=["user1", "user2"]
        )
        self.message = ConversationMessage.objects.create(
            conversation=self.conversation,
            sender_id="user1",
            content="Test message content"
        )

    def test_message_creation(self):
        """Test that a message can be created"""
        self.assertEqual(self.message.sender_id, "user1")
        self.assertEqual(self.message.content, "Test message content")
        self.assertEqual(self.message.conversation, self.conversation)
        self.assertFalse(self.message.is_read)
        self.assertIsNotNone(self.message.created_at)

    def test_message_str_representation(self):
        """Test the string representation of a message"""
        expected = "user1: Test message content..."
        self.assertEqual(str(self.message), expected)

    def test_message_ordering(self):
        """Test that messages are ordered by creation time"""
        message2 = ConversationMessage.objects.create(
            conversation=self.conversation,
            sender_id="user2",
            content="Second message"
        )

        messages = list(self.conversation.messages.all())
        self.assertEqual(messages[0], self.message)
        self.assertEqual(messages[1], message2)

    def test_message_read_status(self):
        """Test that message read status can be updated"""
        self.assertFalse(self.message.is_read)

        self.message.is_read = True
        self.message.save()

        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)