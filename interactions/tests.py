import os
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from communities.models import Community
from users.models import User
from interactions.models import Block
from posts.models import Post

class InteractionTestCase(APITestCase):
    def setUp(self):
        self.my_id = "acde070d-8c4c-4f0d-9d8a-162843c10333"
        self.other_id = "550e8400-e29b-41d4-a716-446655440000"

        self.me = User.objects.create(user_id=self.my_id, username="me")
        self.other_user = User.objects.create(user_id=self.other_id, username="other")
        
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {os.getenv("TEST_VERISAFE_JWT")}"}
        
        self.client.defaults['user_id'] = self.my_id

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_block_user_success(self, mock_verify):
        """Tests that a user can block another user."""
        
        mock_verify.return_value = {"sub": self.my_id, "name": "Tester"}

        url = reverse("block-list-create")
        payload = {
            "blocked_user": self.other_id,
            "block_type": "user"
        }

        response = self.client.post(url, payload, format="json", **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Block.objects.filter(blocker=self.me, blocked_user=self.other_user).exists()
        )

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_mutual_blocking_feed_exclusion(self, mock_verify):
        """Tests that mutual blocking works: I shouldn't see posts from someone who blocked me."""
        
        mock_verify.return_value = {"sub": self.my_id}

        test_community = Community.objects.create(
            name="Test Community",
            description="A place for testing",
            creator=self.other_user
        )

        Block.objects.create(blocker=self.other_user, blocked_user=self.me, block_type='user')

        Post.objects.create(
            author=self.other_user, 
            title="Hidden Content", 
            community=test_community
        )

        url = reverse("post-feed")
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, "Hidden Content")

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_unblock_user(self, mock_verify):
        """Tests unblocking a user."""
        mock_verify.return_value = {"sub": self.my_id}
        
        block = Block.objects.create(blocker=self.me, blocked_user=self.other_user, block_type='user')
        
        url = reverse("unblock", kwargs={"id": block.id})
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Block.objects.filter(id=block.id).exists())

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_cannot_block_self(self, mock_verify):
        """Ensures a user cannot create a block record for themselves."""
        mock_verify.return_value = {"sub": self.my_id}
        
        url = reverse("block-list-create")
        payload = {
            "blocked_user": self.my_id,
            "block_type": "user"
        }

        response = self.client.post(url, payload, format="json", **self.auth_headers)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_duplicate_block_prevention(self, mock_verify):
        """Ensures that a user cannot block the same user twice."""
        mock_verify.return_value = {"sub": self.my_id}

        Block.objects.create(blocker=self.me, blocked_user=self.other_user, block_type='user')
        
        url = reverse("block-list-create")
        payload = {
            "blocked_user": self.other_id,
            "block_type": "user"
        }
        
        response = self.client.post(url, payload, format="json", **self.auth_headers)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_blocked_community_feed_exclusion(self, mock_verify):
        """Tests that blocking a community hides its posts from the feed."""
        mock_verify.return_value = {"sub": self.my_id}

        community_to_block = Community.objects.create(
            name="Spam City",
            description="Annoying posts here",
            creator=self.other_user
        )

        Block.objects.create(blocker=self.me, blocked_community=community_to_block, block_type='community')

        Post.objects.create(
            author=self.other_user, 
            title="Community Post", 
            community=community_to_block
        )

        response = self.client.get(reverse("post-feed"), **self.auth_headers)

        self.assertNotContains(response, "Community Post")

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_report_post_success(self, mock_verify):
        """Tests reporting a specific post."""
        mock_verify.return_value = {"sub": self.my_id}

        test_community = Community.objects.create(name="Report Test", creator=self.other_user)
        reported_post = Post.objects.create(author=self.other_user, title="Offensive", community=test_community)

        payload = {
            "reported_user": self.other_id,
            "reported_post": reported_post.id,
            "report_type": "post",
            "reason": "Inappropriate content"
        }

        url = reverse("report-create")

        response = self.client.post(url, payload, format="json", **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from interactions.models import Report
        self.assertTrue(Report.objects.filter(reporter=self.me, reported_post=reported_post).exists())

    @patch('chirp.verisafe_authentication.verify_verisafe_jwt')
    def test_unblock_permission_denied(self, mock_verify):
        """Tests that a user cannot delete a block created by someone else."""
        attacker_id = "00000000-0000-0000-0000-000000000000"
        User.objects.create(user_id=attacker_id, username="attacker")
        
        mock_verify.return_value = {"sub": attacker_id}
        
        block = Block.objects.create(blocker=self.me, blocked_user=self.other_user, block_type='user')
        
        self.client.defaults['user_id'] = attacker_id
        url = reverse("unblock", kwargs={"id": block.id})
        
        response = self.client.delete(url, **self.auth_headers)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)