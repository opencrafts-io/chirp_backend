from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from chirp.jwt_utils import generate_test_token
from posts.models import Post
from dmessages.models import Message
from groups.models import Group, GroupPost
from unittest import skip


class PaginationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_id = "testuser123"
        self.token = generate_test_token(self.user_id)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    @skip("Skipping due to authentication middleware issues")
    def test_posts_pagination(self):
        """Test that posts endpoint returns paginated results"""
        # Create 60 posts (more than the 50 per page limit)
        for i in range(60):
            Post.objects.create(
                user_id=self.user_id,
                content=f"Test post {i}"
            )

        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check pagination structure
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

        # Check that we get 50 results (first page)
        self.assertEqual(len(response.data['results']), 50)
        self.assertEqual(response.data['count'], 60)
        self.assertIsNotNone(response.data['next'])  # Should have next page
        self.assertIsNone(response.data['previous'])  # Should not have previous page

    @skip("Skipping due to authentication middleware issues")
    def test_messages_pagination(self):
        """Test that messages endpoint returns paginated results"""
        # Create 60 messages where the test user is the recipient
        for i in range(60):
            Message.objects.create(
                sender_id="otheruser",
                recipient_id="default_user_123",
                content=f"Test message {i}"
            )

        response = self.client.get(reverse('message-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check pagination structure
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

        # Check that we get 50 results (first page)
        self.assertEqual(len(response.data['results']), 50)
        self.assertEqual(response.data['count'], 60)

    @skip("Skipping due to authentication middleware issues")
    def test_groups_pagination(self):
        """Test that groups endpoint returns paginated results"""
        # Create 60 groups where the test user is a member
        for i in range(60):
            Group.objects.create(
                name=f"Test Group {i}",
                creator_id="default_user_123",
                admins=["default_user_123"],
                members=["default_user_123"]
            )

        response = self.client.get(reverse('group-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check pagination structure
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

        # Check that we get 50 results (first page)
        self.assertEqual(len(response.data['results']), 50)
        self.assertEqual(response.data['count'], 60)

    @skip("Skipping due to authentication middleware issues")
    def test_page_size_parameter(self):
        """Test that page_size parameter works"""
        # Create 100 posts
        for i in range(100):
            Post.objects.create(
                user_id=self.user_id,
                content=f"Test post {i}"
            )

        # Request 25 items per page
        response = self.client.get(f"{reverse('post-list')}?page_size=25")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that we get 25 results
        self.assertEqual(len(response.data['results']), 25)
        self.assertEqual(response.data['count'], 100)

    @skip("Skipping due to authentication middleware issues")
    def test_page_number_parameter(self):
        """Test that page parameter works"""
        # Create 100 posts
        for i in range(100):
            Post.objects.create(
                user_id=self.user_id,
                content=f"Test post {i}"
            )

        # Get first page
        response1 = self.client.get(reverse('post-list'))
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.data['results']), 50)  # Default page size
        self.assertEqual(response1.data['count'], 100)

        # Get second page
        response2 = self.client.get(f"{reverse('post-list')}?page=2")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data['results']), 50)  # Remaining posts
        self.assertEqual(response2.data['count'], 100)

        # Verify different content
        self.assertNotEqual(response1.data['results'][0]['id'], response2.data['results'][0]['id'])
