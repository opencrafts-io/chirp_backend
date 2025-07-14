from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from ..models import Post, PostLike
from chirp.jwt_utils import generate_test_token
from django.db.models import F


class PostLikeTest(APITestCase):
    def setUp(self):
        """Set up test data and authenticated client."""
        self.client = APIClient()
        self.user_id = 'testuser123'
        self.other_user_id = 'otheruser456'
        self.post_owner_id = 'postowner789'

        # Authenticate the primary test user
        token = generate_test_token(self.user_id)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        # Create a post by another user
        self.post = Post.objects.create(user_id=self.post_owner_id, content="A post to be liked.")
        self.like_url = reverse('post-like', kwargs={'pk': self.post.pk})
        self.list_url = reverse('post-list')

    def test_like_post(self):
        """Test that a user can like a post."""
        response = self.client.post(self.like_url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'liked')
        self.assertEqual(Post.objects.get(pk=self.post.pk).like_count, 1)
        self.assertTrue(PostLike.objects.filter(user_id=self.user_id, post=self.post).exists())

    def test_like_post_twice(self):
        """Test that liking a post twice does not create a duplicate like."""
        self.client.post(self.like_url, {})  # First like
        response = self.client.post(self.like_url, {})  # Second like
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'already liked')
        self.assertEqual(Post.objects.get(pk=self.post.pk).like_count, 1)

    def test_unlike_post(self):
        """Test that a user can unlike a post."""
        self.client.post(self.like_url, {})  # Like the post first
        self.assertEqual(Post.objects.get(pk=self.post.pk).like_count, 1)

        response = self.client.delete(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.get(pk=self.post.pk).like_count, 0)
        self.assertFalse(PostLike.objects.filter(user_id=self.user_id, post=self.post).exists())

    def test_unlike_post_not_liked(self):
        """Test that unliking a post that isn't liked returns an error."""
        response = self.client.delete(self.like_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_like_count_and_is_liked_in_list(self):
        """Test that like_count and is_liked are in the post list response."""
        # Another user likes the post, manually update the count for the test
        PostLike.objects.create(user_id=self.other_user_id, post=self.post)
        Post.objects.filter(pk=self.post.pk).update(like_count=F('like_count') + 1)
        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, 1)

        # The authenticated user likes the post
        self.client.post(self.like_url, {})
        self.post.refresh_from_db()

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        post_data = response.data[0]
        self.assertEqual(post_data['like_count'], 2)
        self.assertTrue(post_data['is_liked'])

    def test_is_liked_false_in_list(self):
        """Test that is_liked is false when the user has not liked the post."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        post_data = response.data[0]
        self.assertEqual(post_data['like_count'], 0)
        self.assertFalse(post_data['is_liked'])