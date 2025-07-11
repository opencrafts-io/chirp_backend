import io
import json
import shutil
import tempfile

import jwt
from django.conf import settings
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from chirp.jwt_utils import generate_test_token
from ..models import Tweets

# Define a temporary directory for media files
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TweetWithImageEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.tweets_url = '/statuses/'
        self.test_user_id = 'user123'

    def tearDown(self):
        """Clean up the temporary media directory after tests."""
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def _create_test_image(self, name='test.png', ext='png', size=(50, 50), color=(255, 0, 0)):
        """Generate a simple in-memory image for testing."""
        file_obj = io.BytesIO()
        image = Image.new("RGB", size=size, color=color)
        image.save(file_obj, ext)
        file_obj.name = name
        file_obj.seek(0)
        return file_obj

    def test_post_tweet_with_image(self):
        """Test creating a tweet with an image."""
        image = self._create_test_image()
        data = {
            'content': 'A tweet with an image!',
            'image': image
        }
        response = self.client.post(
            self.tweets_url,
            data,
            format='multipart',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tweets.objects.count(), 1)
        tweet = Tweets.objects.first()
        self.assertIn('image', response.data)
        self.assertTrue(tweet.image.url.startswith('/media/tweet_images/test'))

    def test_post_tweet_with_image_and_no_content(self):
        """Test creating a tweet with an image and no text content."""
        image = self._create_test_image(name='test2.png')
        data = {'image': image, 'content': ''}
        response = self.client.post(
            self.tweets_url,
            data,
            format='multipart',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('image', response.data)
        self.assertTrue(response.data['image'].startswith('/media/tweet_images/test2'))

    def test_post_tweet_without_image(self):
        """Test that creating a tweet without an image still works."""
        data = {'content': 'A tweet without an image.'}
        response = self.client.post(
            self.tweets_url,
            data,
            format='multipart',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('image', response.data)
        self.assertIsNone(response.data.get('image'))

    def test_post_tweet_with_invalid_file(self):
        """Test that uploading a non-image file is rejected."""
        invalid_file = io.BytesIO(b"this is not an image")
        invalid_file.name = 'test.txt'
        data = {
            'content': 'Trying to upload a text file.',
            'image': invalid_file
        }
        response = self.client.post(
            self.tweets_url,
            data,
            format='multipart',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)