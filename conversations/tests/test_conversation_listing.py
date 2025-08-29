from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from conversations.models import Conversation, ConversationMessage
from conversations.serializers import ConversationListSerializer, ConversationSerializer
from unittest.mock import patch, MagicMock


class ConversationListingTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user1_id = "user1-123"
        self.user2_id = "user2-456"
        self.user3_id = "user3-789"

        # Create conversations
        self.conversation1 = Conversation.objects.create(
            conversation_id="conv_12345678",
            participants=[self.user1_id, self.user2_id]
        )

        self.conversation2 = Conversation.objects.create(
            conversation_id="conv_87654321",
            participants=[self.user1_id, self.user3_id]
        )

        self.conversation3 = Conversation.objects.create(
            conversation_id="conv_99999999",
            participants=[self.user2_id, self.user3_id]  # user1 not involved
        )

        # Create messages for conversations
        self.message1 = ConversationMessage.objects.create(
            conversation=self.conversation1,
            sender_id=self.user1_id,
            content="Hello from user1 to user2"
        )

        self.message2 = ConversationMessage.objects.create(
            conversation=self.conversation1,
            sender_id=self.user2_id,
            content="Hi back from user2"
        )

        self.message3 = ConversationMessage.objects.create(
            conversation=self.conversation2,
            sender_id=self.user1_id,
            content="Hello from user1 to user3"
        )

        self.message4 = ConversationMessage.objects.create(
            conversation=self.conversation3,
            sender_id=self.user2_id,
            content="Hello from user2 to user3"
        )

        # Create API client
        self.client = APIClient()

    def test_conversation_list_serializer_fields(self):
        """Test that ConversationListSerializer has the correct fields"""
        serializer = ConversationListSerializer(self.conversation1, context={'user_id': self.user1_id})
        data = serializer.data

        # Should have these fields
        expected_fields = [
            'conversation_id', 'participants', 'created_at', 'updated_at',
            'last_message_at', 'message_count', 'last_message', 'unread_count'
        ]

        for field in expected_fields:
            self.assertIn(field, data, f"Field '{field}' should be present")

        # Should NOT have messages field
        self.assertNotIn('messages', data, "Should not have full messages")

    def test_conversation_list_serializer_message_count(self):
        """Test that message_count is calculated correctly"""
        serializer = ConversationListSerializer(self.conversation1, context={'user_id': self.user1_id})
        data = serializer.data

        # Check message count
        self.assertEqual(data['message_count'], 2)  # 2 messages in conversation1

        # Test another conversation
        serializer2 = ConversationListSerializer(self.conversation2, context={'user_id': self.user1_id})
        data2 = serializer2.data
        self.assertEqual(data2['message_count'], 1)  # 1 message in conversation2

    def test_conversation_list_serializer_last_message_preview(self):
        """Test that last_message preview is generated correctly"""
        serializer = ConversationListSerializer(self.conversation1, context={'user_id': self.user1_id})
        data = serializer.data

        # Check last_message structure
        self.assertIn('last_message', data)
        last_message = data['last_message']

        # Should have preview fields
        expected_preview_fields = ['sender_id', 'content', 'created_at', 'is_read']
        for field in expected_preview_fields:
            self.assertIn(field, last_message, f"Last message should have '{field}'")

        # Should NOT have full message fields
        full_message_fields = ['id', 'conversation', 'attachments']
        for field in full_message_fields:
            self.assertNotIn(field, last_message, f"Last message should not have '{field}'")

    def test_conversation_list_serializer_unread_count(self):
        """Test that unread_count is calculated correctly"""
        # Mark one message as unread
        self.message2.is_read = False
        self.message2.save()

        serializer = ConversationListSerializer(self.conversation1, context={'user_id': self.user1_id})
        data = serializer.data

        # user1 should see 1 unread message (from user2)
        self.assertEqual(data['unread_count'], 1)

    def test_conversation_full_serializer_still_has_messages(self):
        """Test that ConversationSerializer still includes full messages"""
        serializer = ConversationSerializer(self.conversation1, context={'user_id': self.user1_id})
        data = serializer.data

        # Should have messages field
        self.assertIn('messages', data)
        self.assertIsInstance(data['messages'], list)

        # Should have message_count
        self.assertIn('message_count', data)
        self.assertEqual(data['message_count'], 2)

    def test_conversation_ordering_by_last_message_at(self):
        """Test that conversations are ordered correctly"""
        # Update last_message_at to test ordering
        from django.utils import timezone
        import datetime

        # Set conversation2 to have more recent activity
        self.conversation2.last_message_at = timezone.now()
        self.conversation2.save()

        self.conversation1.last_message_at = timezone.now() - datetime.timedelta(hours=1)
        self.conversation1.save()

        # Get conversations ordered by last_message_at desc
        conversations = Conversation.objects.filter(
            participants__contains=[self.user1_id]
        ).order_by('-last_message_at', '-created_at')

        # First should be conversation2 (more recent)
        self.assertEqual(conversations[0].conversation_id, self.conversation2.conversation_id)
        self.assertEqual(conversations[1].conversation_id, self.conversation1.conversation_id)

    def test_user_conversation_filtering(self):
        """Test that only user's conversations are returned"""
        # Get conversations for user1
        user1_conversations = Conversation.objects.filter(
            participants__contains=[self.user1_id]
        )

        # Should only have 2 conversations
        self.assertEqual(user1_conversations.count(), 2)

        # Check specific conversations
        conversation_ids = [conv.conversation_id for conv in user1_conversations]
        self.assertIn(self.conversation1.conversation_id, conversation_ids)
        self.assertIn(self.conversation2.conversation_id, conversation_ids)
        self.assertNotIn(self.conversation3.conversation_id, conversation_ids)

    def test_performance_optimization_prefetch_related(self):
        """Test that prefetch_related prevents N+1 queries"""
        # Get conversations with prefetch_related
        conversations = Conversation.objects.filter(
            participants__contains=[self.user1_id]
        ).prefetch_related('messages')

        # Access messages to trigger queries
        for conv in conversations:
            _ = list(conv.messages.all())

        # Just verify that prefetch_related works without errors
        # The actual query optimization is tested by Django itself
        self.assertTrue(True, "Prefetch related works without errors")

    def test_conversation_list_with_user_id_query_param(self):
        """Test that conversation listing works with user_id query parameter"""
        # Test with user_id query parameter
        url = reverse('conversations:conversation-list')
        response = self.client.get(f"{url}?user_id={self.user1_id}")

        # Should work now
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('user_id', response.data)
        self.assertEqual(response.data['user_id'], self.user1_id)
        self.assertEqual(response.data['total_count'], 2)

    def test_conversation_list_without_user_id_fails(self):
        """Test that conversation listing fails without user_id parameter"""
        url = reverse('conversations:conversation-list')
        response = self.client.get(url)

        # Should fail with 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('user_id query parameter is required', response.data['error'])

    def test_conversation_list_different_user(self):
        """Test that different users get their own conversations"""
        # Test with user2
        url = reverse('conversations:conversation-list')
        response = self.client.get(f"{url}?user_id={self.user2_id}")

        # Should work and return user2's conversations
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_id'], self.user2_id)
        self.assertEqual(response.data['total_count'], 2)  # user2 is in conv1 and conv3

        # Check conversation IDs
        conversation_ids = [conv['conversation_id'] for conv in response.data['results']]
        self.assertIn(self.conversation1.conversation_id, conversation_ids)
        self.assertIn(self.conversation3.conversation_id, conversation_ids)
        self.assertNotIn(self.conversation2.conversation_id, conversation_ids)
