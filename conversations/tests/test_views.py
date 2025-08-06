from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from chirp.jwt_utils import generate_test_token
from conversations.models import Conversation, ConversationMessage
import os
import shutil

# Use a temporary directory for media files during tests
TEST_MEDIA_DIR = "test_media_conversations"


@override_settings(MEDIA_ROOT=TEST_MEDIA_DIR)
class ConversationAttachmentTest(APITestCase):
    def setUp(self):
        self.user_id = "default_user_123"
        self.token = generate_test_token(self.user_id)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Create a conversation
        self.conversation = Conversation.objects.create(
            conversation_id="conv_test123",
            participants=[self.user_id, "user2"]
        )

        # Ensure the test media directory exists
        os.makedirs(TEST_MEDIA_DIR, exist_ok=True)

    def tearDown(self):
        # Clean up the temporary media directory
        if os.path.exists(TEST_MEDIA_DIR):
            shutil.rmtree(TEST_MEDIA_DIR)

    def _get_image(self, name="test_image.png"):
        # A 1x1 transparent PNG
        return SimpleUploadedFile(
            name,
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82",
            "image/png",
        )

    def test_create_message_with_attachment(self):
        """Test creating a conversation message with an image attachment"""
        url = reverse('conversations:conversation-messages', kwargs={'conversation_id': self.conversation.conversation_id})
        image = self._get_image()
        data = {"content": "Message with attachment", "attachments": [image]}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("attachments", response.data)
        self.assertEqual(len(response.data["attachments"]), 1)

        attachment_data = response.data["attachments"][0]
        self.assertIn("file_url", attachment_data)
        self.assertIn("message_attachments/test_image", attachment_data["file_url"])
        self.assertEqual(attachment_data["attachment_type"], "image")
        self.assertIn("file_size_mb", attachment_data)
        self.assertIn("original_filename", attachment_data)

    def test_create_message_without_content_but_with_attachment(self):
        """Test creating a message with only attachment (no content)"""
        url = reverse('conversations:conversation-messages', kwargs={'conversation_id': self.conversation.conversation_id})
        image = self._get_image()
        data = {"attachments": [image]}  # No content
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "")
        self.assertEqual(len(response.data["attachments"]), 1)

    def test_create_message_with_multiple_attachments(self):
        """Test creating a message with multiple attachments"""
        url = reverse('conversations:conversation-messages', kwargs={'conversation_id': self.conversation.conversation_id})
        image1 = self._get_image("test1.png")
        image2 = self._get_image("test2.png")
        data = {"content": "Message with multiple attachments", "attachments": [image1, image2]}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["attachments"]), 2)

        # Check that both attachments have URLs
        for attachment in response.data["attachments"]:
            self.assertIn("file_url", attachment)
            self.assertEqual(attachment["attachment_type"], "image")


class ConversationViewsTest(APITestCase):
    def setUp(self):
        self.user_id = "default_user_123"
        self.conversation = Conversation.objects.create(
            conversation_id="conv_test123",
            participants=[self.user_id, "user2"]
        )
        self.message = ConversationMessage.objects.create(
            conversation=self.conversation,
            sender_id=self.user_id,
            content="Test message"
        )

    def test_conversation_list_view(self):
        """Test getting all conversations for a user"""
        response = self.client.get(reverse('conversations:conversation-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['conversation_id'], 'conv_test123')

    def test_conversation_detail_view(self):
        """Test getting conversation details"""
        response = self.client.get(reverse('conversations:conversation-detail', kwargs={'conversation_id': 'conv_test123'}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['conversation_id'], 'conv_test123')

    def test_conversation_create_view(self):
        """Test creating a new conversation"""
        data = {
            'participants': ["new_user"]  # The view will automatically add the default user
        }
        response = self.client.post(reverse('conversations:conversation-create'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_conversation_messages_view(self):
        """Test getting messages for a conversation"""
        response = self.client.get(reverse('conversations:conversation-messages', kwargs={'conversation_id': 'conv_test123'}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Test message')

    def test_create_message_in_conversation(self):
        """Test creating a new message in a conversation"""
        data = {'content': 'New message'}
        response = self.client.post(reverse('conversations:conversation-messages', kwargs={'conversation_id': 'conv_test123'}), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'New message')


class ConversationSerializerTest(TestCase):
    def setUp(self):
        self.conversation = Conversation.objects.create(
            conversation_id="conv_test123",
            participants=["user1", "user2"]
        )
        self.message = ConversationMessage.objects.create(
            conversation=self.conversation,
            sender_id="user1",
            content="Test message"
        )

    def test_conversation_serializer(self):
        """Test conversation serializer"""
        from conversations.serializers import ConversationSerializer

        serializer = ConversationSerializer(self.conversation, context={'user_id': 'user1'})
        data = serializer.data

        self.assertEqual(data['conversation_id'], "conv_test123")
        self.assertEqual(data['participants'], ["user1", "user2"])
        self.assertIn('messages', data)
        self.assertIn('last_message', data)
        self.assertIn('unread_count', data)

    def test_conversation_message_serializer(self):
        """Test conversation message serializer"""
        from conversations.serializers import ConversationMessageSerializer

        serializer = ConversationMessageSerializer(self.message)
        data = serializer.data

        self.assertEqual(data['sender_id'], "user1")
        self.assertEqual(data['content'], "Test message")
        self.assertFalse(data['is_read'])
        self.assertIn('created_at', data)