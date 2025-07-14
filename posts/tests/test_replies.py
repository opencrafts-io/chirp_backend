
import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from chirp.jwt_utils import generate_test_token
from ..models import Post, PostReply



class PostReplyEndpointTest(TestCase):
  def setUp(self):

    self.client = APIClient()
    self.user_id = 'user123'
    self.test_user_id_2 = 'user456'

    self.parent_post = Post.objects.create(
      user_id=self.user_id,
      content='This is a parent post'
    )

    self.reply_url = f'/statuses/{self.parent_post.id}/replies/'
    self.valid_reply_data = {'content': 'This is a valid reply'}

  def _get_auth_headers(self, user_id=None):
    user_id = user_id or self.user_id
    token = generate_test_token(user_id)
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

  def test_create_reply_authenticated(self):
    response = self.client.post(
      self.reply_url,
      data=json.dumps(self.valid_reply_data),
      content_type='application/json',
      **self._get_auth_headers(self.test_user_id_2)
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(PostReply.objects.count(), 1)
    reply = PostReply.objects.first()
    self.assertEqual(reply.user_id, self.test_user_id_2)
    self.assertEqual(reply.parent_post, self.parent_post)
    self.assertEqual(reply.content, self.valid_reply_data['content'])

  def test_create_reply_unauthenticated(self):
        """Test creating a reply without a token fails."""
        response = self.client.post(
            self.reply_url,
            data=json.dumps(self.valid_reply_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_get_replies_authenticated(self):
        """Test getting replies with a valid token succeeds."""
        PostReply.objects.create(
            parent_post=self.parent_post,
            user_id=self.test_user_id_2,
            content="Another reply"
        )
        response = self.client.get(self.reply_url, **self._get_auth_headers())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

  def test_get_replies_unauthenticated(self):
        """Test getting replies without a token fails."""
        response = self.client.get(self.reply_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_reply_to_nonexistent_post(self):
        """Test that replying to a non-existent post returns a 404 error."""
        invalid_url = '/statuses/9999/replies/'
        response = self.client.post(
            invalid_url,
            data=json.dumps(self.valid_reply_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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