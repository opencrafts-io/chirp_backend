import shutil
import tempfile
from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from ..models import Post
from chirp.jwt_utils import generate_test_token


class PostImageUploadTest(APITestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()

        self.client = APIClient()
        self.list_url = reverse('post-list')
        self.user_id = 'testuser123'
        token = generate_test_token(self.user_id)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        self.post = Post.objects.create(user_id=self.user_id, content='Initial post.')
        self.detail_url = reverse('post-detail', kwargs={'pk': self.post.pk})

    def tearDown(self):
        """Remove the temporary media directory and disable settings override."""
        shutil.rmtree(self.media_root)
        self.settings_override.disable()

    def _get_image(self):
        """Helper method to get a SimpleUploadedFile for testing image uploads."""
        # A valid, minimal 1x1 black PNG
        image_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00'
            b'\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return SimpleUploadedFile("test_image.png", image_data, content_type="image/png")

    def test_create_post_with_image(self):
        """Test creating a post with an image."""
        data = {
            'content': 'A post with an image!',
            'image': self._get_image()
        }
        response = self.client.post(self.list_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)
        self.assertTrue(Post.objects.latest('id').image.name.startswith('post_images/test_image'))

    def test_create_post_with_image_only(self):
        """Test creating a post with only an image and no content."""
        data = {'image': self._get_image(), 'content': ''}
        response = self.client.post(self.list_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)

    def test_create_post_no_content_no_image(self):
        """Test creating a post with no content and no image fails."""
        data = {'content': ''}
        response = self.client.post(self.list_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_post_with_image(self):
        """Test updating a post with an image."""
        data = {
            'content': 'Updated post content.',
            'image': self._get_image()
        }
        response = self.client.put(self.detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertTrue(self.post.image.name.startswith('post_images/test_image'))

    def test_image_url_in_post_response(self):
        """Test that the image URL is included in the post's API response."""
        post_with_image = Post.objects.create(
            user_id=self.user_id,
            content="A post with an image.",
            image=self._get_image()
        )
        url = reverse('post-detail', kwargs={'pk': post_with_image.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image', response.data)
        self.assertTrue(response.data['image'].startswith('/media/post_images/test_image'))