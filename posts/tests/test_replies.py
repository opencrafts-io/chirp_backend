
import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from chirp.jwt_utils import generate_test_token
from ..models import Post, Comment
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from chirp.jwt_utils import generate_test_token
from posts.models import Post, Comment
from groups.models import Group
import unittest


@unittest.skip("JWT authentication disabled for development")
class PostReplyEndpointTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_id = "testuser"
        self.token = generate_test_token(self.user_id)

        # Create a group for the post
        self.group, _ = Group.objects.get_or_create(
            id=998,
            defaults={
                "name": "Test Group",
                "description": "Test group",
                "creator_id": self.user_id,
                "is_private": False
            }
        )

        self.post = Post.objects.create(
            user_id=self.user_id,
            content="Original Post",
            group=self.group
        )
        self.reply_url = reverse("post-comments", kwargs={"post_id": self.post.pk})

    def test_create_reply_authenticated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        data = {"content": "A reply from an authenticated user."}
        response = self.client.post(self.reply_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().content, data["content"])

    def test_create_reply_unauthenticated(self):
        # No token provided
        data = {"content": "A reply from an unauthenticated user."}
        response = self.client.post(self.reply_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CommentModelTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.group, _ = Group.objects.get_or_create(
            id=997,
            defaults={
                "name": "Test Group",
                "description": "Test group for comments",
                "creator_id": "creator123",
                "is_private": False
            }
        )

        self.post_user_id = 'user123'
        self.reply_user_id = 'user456'
        self.post = Post.objects.create(
            user_id=self.post_user_id,
            content='This is the parent post.',
            group=self.group
        )
        self.valid_comment_data = {
            'post': self.post,
            'user_id': self.reply_user_id,
            'user_name': 'Test User',
            'content': 'This is a test comment.'
        }

    def test_create_valid_comment(self):
        """Test creating a valid comment."""
        comment = Comment.objects.create(**self.valid_comment_data)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.user_id, self.reply_user_id)
        self.assertEqual(comment.content, 'This is a test comment.')
        self.assertIsNotNone(comment.created_at)
        self.assertIsNotNone(comment.updated_at)

    def test_comment_string_representation(self):
        """Test the __str__ method of the comment."""
        comment = Comment.objects.create(**self.valid_comment_data)
        expected_str = f"Comment by {self.reply_user_id} on post: {self.post.content[:50]}..."
        self.assertEqual(str(comment), expected_str)

    def test_comment_post_cascade_delete(self):
        """Test that deleting a post also deletes its comments."""
        comment = Comment.objects.create(**self.valid_comment_data)
        self.assertEqual(Comment.objects.count(), 1)
        self.post.delete()
        self.assertEqual(Comment.objects.count(), 0)

    def test_multiple_comments_to_same_post(self):
        """Test that multiple comments can be added to the same post."""
        comment1 = Comment.objects.create(**self.valid_comment_data)
        comment2_data = self.valid_comment_data.copy()
        comment2_data['content'] = 'This is a second comment.'
        comment2 = Comment.objects.create(**comment2_data)

        self.assertEqual(self.post.comments.count(), 2)
        self.assertIn(comment1, self.post.comments.all())
        self.assertIn(comment2, self.post.comments.all())