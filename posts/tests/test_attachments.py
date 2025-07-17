import os
import shutil
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from chirp.jwt_utils import generate_test_token
from posts.models import Post

# Use a temporary directory for media files during tests
TEST_MEDIA_DIR = "test_media"


@override_settings(MEDIA_ROOT=TEST_MEDIA_DIR)
class PostAttachmentUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_id = "testuser123"
        self.token = generate_test_token(self.user_id)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.post = Post.objects.create(user_id=self.user_id, content="A post.")

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

    def test_create_post_with_attachment(self):
        url = reverse("post-create")
        image = self._get_image()
        data = {"content": "Post with an attachment", "attachments": [image]}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)
        new_post = Post.objects.latest("created_at")
        self.assertEqual(new_post.attachments.count(), 1)
        self.assertTrue(new_post.attachments.first().file.name.startswith("attachments/"))

    def test_create_post_with_multiple_attachments(self):
        url = reverse("post-create")
        image1 = self._get_image("test1.png")
        image2 = self._get_image("test2.png")
        data = {"content": "Post with two attachments", "attachments": [image1, image2]}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_post = Post.objects.latest("created_at")
        self.assertEqual(new_post.attachments.count(), 2)

    def test_create_post_no_content_with_attachment(self):
        url = reverse("post-create")
        image = self._get_image()
        data = {"attachments": [image]} # No content
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.latest("created_at").content, "")


    def test_attachment_url_in_post_response(self):
        url = reverse("post-create")
        image = self._get_image()
        data = {"content": "A post to check attachment URL", "attachments": [image]}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("attachments", response.data)
        self.assertEqual(len(response.data["attachments"]), 1)
        attachment_data = response.data["attachments"][0]
        self.assertIn("file", attachment_data)
        self.assertIn("attachments/test_image", attachment_data["file"])