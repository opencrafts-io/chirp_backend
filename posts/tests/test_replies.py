
import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from chirp.jwt_utils import generate_test_token
from ..models import Post, PostReply
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from chirp.jwt_utils import generate_test_token
from posts.models import Post, PostReply
import unittest


@unittest.skip("JWT authentication disabled for development")
class PostReplyEndpointTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_id = "testuser"
        self.token = generate_test_token(self.user_id)
        self.post = Post.objects.create(user_id=self.user_id, content="Original Post")
        self.reply_url = reverse("post-reply", kwargs={"post_id": self.post.pk})

    def test_create_reply_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        data = {"content": "A reply from an authenticated user."}
        response = self.client.post(self.reply_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PostReply.objects.count(), 1)
        self.assertEqual(PostReply.objects.first().content, data["content"])

    def test_create_reply_unauthenticated(self):
        # No token provided
        data = {"content": "A reply from an unauthenticated user."}
        response = self.client.post(self.reply_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PostReplyModelTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.post_user_id = 'user123'
        self.reply_user_id = 'user456'
        self.post = Post.objects.create(user_id=self.post_user_id, content='This is the parent post.')
        self.valid_reply_data = {
            'parent_post': self.post,
            'user_id': self.reply_user_id,
            'content': 'This is a test reply.'
        }

    def test_create_valid_reply(self):
        """Test creating a valid reply."""
        reply = PostReply.objects.create(**self.valid_reply_data)
        self.assertEqual(reply.parent_post, self.post)
        self.assertEqual(reply.user_id, self.reply_user_id)
        self.assertEqual(reply.content, 'This is a test reply.')
        self.assertIsNotNone(reply.created_at)
        self.assertIsNotNone(reply.updated_at)

    def test_reply_string_representation(self):
        """Test the __str__ method of the reply."""
        reply = PostReply.objects.create(**self.valid_reply_data)
        expected_str = f"Reply by {self.reply_user_id}: to post {self.post.content}"
        self.assertEqual(str(reply), expected_str)

    def test_reply_parent_post_cascade_delete(self):
        """Test that deleting a post also deletes its replies."""
        reply = PostReply.objects.create(**self.valid_reply_data)
        self.assertEqual(PostReply.objects.count(), 1)
        self.post.delete()
        self.assertEqual(PostReply.objects.count(), 0)

    def test_multiple_replies_to_same_post(self):
        """Test that multiple replies can be added to the same post."""
        reply1 = PostReply.objects.create(**self.valid_reply_data)
        reply2_data = self.valid_reply_data.copy()
        reply2_data['content'] = 'This is a second reply.'
        reply2 = PostReply.objects.create(**reply2_data)

        self.assertEqual(self.post.replies.count(), 2)
        self.assertIn(reply1, self.post.replies.all())
        self.assertIn(reply2, self.post.replies.all())