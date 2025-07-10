
import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from chirp.jwt_utils import generate_test_token
from ..models import Tweets, TweetReply



class TweetReplyEndpointTest(TestCase):
  def setUp(self):

    self.client = APIClient()
    self.user_id = 'user123'
    self.test_user_id_2 = 'user456'

    self.parent_tweet = Tweets.objects.create(
      user_id=self.user_id,
      content='This is a parent tweet'
    )

    self.reply_url = f'/statuses/{self.parent_tweet.id}/replies/'
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
    self.assertEqual(TweetReply.objects.count(), 1)
    reply = TweetReply.objects.first()
    self.assertEqual(reply.user_id, self.test_user_id_2)
    self.assertEqual(reply.parent_tweet, self.parent_tweet)
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
        TweetReply.objects.create(
            parent_tweet=self.parent_tweet,
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

    def test_reply_to_nonexistent_tweet(self):
        """Test that replying to a non-existent tweet returns a 404 error."""
        invalid_url = '/statuses/9999/replies/'
        response = self.client.post(
            invalid_url,
            data=json.dumps(self.valid_reply_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)