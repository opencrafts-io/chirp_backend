from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from ..models import Post
from chirp.jwt_utils import generate_test_token
from ..models import PostReply


class StatusAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.list_url = reverse('post-list')
        self.valid_post_data = {'content': 'This is a test post from API.'}
        self.invalid_post_data = {'content': ''}
        self.user_id = 'testuser123'
        token = generate_test_token(self.user_id)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        self.post = Post.objects.create(user_id=self.user_id, content='Initial post.')
        self.detail_url = reverse('post-detail', kwargs={'pk': self.post.pk})
        self.reply_url = reverse('post-reply', kwargs={'post_id': self.post.pk})

    def test_create_post(self):
        """Test creating a post with valid data."""
        data = {"content": "This is a test post."}
        response = self.client.post(reverse("post-create"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], data["content"])
        self.assertEqual(response.data["user_id"], self.user_id)

    def test_create_post_invalid_data(self):
        """Test creating a post with invalid data."""
        data = {"content": ""}
        response = self.client.post(reverse("post-create"), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_all_posts(self):
        """Test retrieving all posts."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Initial post.')

    def test_get_single_post(self):
        """Test retrieving a single post."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], self.post.content)

    def test_update_post(self):
        """Test updating a post."""
        update_data = {"content": "Updated content."}
        response = self.client.put(self.detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, update_data["content"])

    def test_partial_update_post(self):
        """Test partially updating a post."""
        update_data = {'content': 'Partially updated post content.'}
        response = self.client.patch(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Partially updated post content.')

    def test_delete_post(self):
        """Test deleting a post."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_delete_non_existent_post(self):
        """Test deleting a post that does not exist."""
        non_existent_url = reverse('post-detail', kwargs={'pk': 999})
        response = self.client.delete(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_reply(self):
        """Test creating a reply to a post."""
        url = reverse("post-reply", kwargs={"post_id": self.post.pk})
        data = {"content": "This is a reply."}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], data["content"])
        self.assertEqual(PostReply.objects.count(), 1)

    def test_create_reply_non_existent_post(self):
        """Test creating a reply to a non-existent post."""
        url = reverse("post-reply", kwargs={"post_id": 999})
        data = {"content": "This should fail."}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)