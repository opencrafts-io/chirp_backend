import json
import jwt
import urllib.parse
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from posts.models import Post
from groups.models import Group, GroupPost, GroupInvite
from dmessages.models import Message
from django.urls import reverse
from chirp.jwt_utils import generate_test_token


class ChirpIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1_id = "user1"
        self.user2_id = "user2"
        self.user3_id = "user3"

        self.token1 = generate_test_token(self.user1_id)
        self.token2 = generate_test_token(self.user2_id)
        self.token3 = generate_test_token(self.user3_id)

    def test_complete_user_workflow(self):
        # User 1 posts a message
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        post_data = {"content": "Hello, world!"}
        response = self.client.post(reverse("post-create"), post_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_id = response.data["id"]

        # User 2 creates a group
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        group_data = {"name": "Test Group", "description": "A group for testing."}
        response = self.client.post(reverse("group-list-create"), group_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group_name = response.data["name"]

        # ... (rest of the workflow remains the same, just ensure auth is handled)

    def test_cross_app_data_consistency(self):
        # User 1 posts a message
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        post_data = {"content": "A test post for consistency."}
        response = self.client.post(
            reverse("post-create"), post_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_id = response.data["id"]

        # Verify the post is in the database
        self.assertTrue(Post.objects.filter(id=post_id).exists())
        # ...

    def test_global_timeline_access(self):
        # User 1 posts a message
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token1}")
        post_data = {"content": "A public post for all to see."}
        response = self.client.post(
            reverse("post-create"), post_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User 2 logs in and views the timeline
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token2}")
        response = self.client.get(reverse("post-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]["content"], post_data["content"])

    # ... (Keep other tests, but ensure they use correct auth and endpoints)