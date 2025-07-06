import json
import jwt
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from tweets.models import Tweets
from groups.models import Group, GroupPost, GroupInvite
from dmessages.models import Message


class ChirpIntegrationTest(TestCase):
    """Integration tests for the Chirp social media platform."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.client = APIClient()

        # Test users
        self.user1_id = 'alice123'
        self.user2_id = 'bob456'
        self.user3_id = 'charlie789'

        # Mock JWT payloads
        self.user1_payload = {'sub': self.user1_id, 'exp': 9999999999}
        self.user2_payload = {'sub': self.user2_id, 'exp': 9999999999}
        self.user3_payload = {'sub': self.user3_id, 'exp': 9999999999}

    def _get_auth_headers(self, user_id):
        """Helper method to get authentication headers for a user."""
        token = jwt.encode({'sub': user_id, 'exp': 9999999999}, 'mock_secret', algorithm='HS256')
        return {'Authorization': f'Bearer {token}'}

    @patch('tweets.middleware.jwt.decode')
    def test_complete_user_workflow(self, mock_jwt_decode):
        """Test complete user workflow: tweet, create group, invite users, send messages."""

        # Step 1: User1 creates a tweet
        mock_jwt_decode.return_value = self.user1_payload
        tweet_data = {'content': 'Hello world! This is my first tweet.'}

        response = self.client.post(
            '/statuses/',
            data=json.dumps(tweet_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tweets.objects.count(), 1)
        created_tweet = Tweets.objects.first()
        self.assertEqual(created_tweet.user_id, self.user1_id)

        # Step 2: User1 creates a group
        group_data = {
            'name': 'Tech Enthusiasts',
            'description': 'A group for tech lovers'
        }

        response = self.client.post(
            '/groups/',
            data=json.dumps(group_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 1)
        created_group = Group.objects.first()
        self.assertEqual(created_group.creator_id, self.user1_id)
        self.assertIn(self.user1_id, created_group.admins)
        self.assertIn(self.user1_id, created_group.members)

        # Step 3: User1 invites User2 to the group
        invite_data = {'invitee_id': self.user2_id}

        response = self.client.post(
            f'/groups/{created_group.id}/invite/',
            data=json.dumps(invite_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupInvite.objects.count(), 1)
        created_invite = GroupInvite.objects.first()
        self.assertEqual(created_invite.invitee_id, self.user2_id)
        self.assertEqual(created_invite.inviter_id, self.user1_id)

        # Step 4: User2 accepts the group invite
        mock_jwt_decode.return_value = self.user2_payload

        response = self.client.post(
            f'/groups/invites/{created_invite.id}/accept/',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_group.refresh_from_db()
        self.assertIn(self.user2_id, created_group.members)
        self.assertEqual(GroupInvite.objects.count(), 0)  # Invite deleted

        # Step 5: User2 posts in the group
        group_post_data = {'content': 'Thanks for inviting me! Excited to be here.'}

        response = self.client.post(
            f'/groups/{created_group.id}/posts/',
            data=json.dumps(group_post_data),
            content_type='application/json',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupPost.objects.count(), 1)
        created_post = GroupPost.objects.first()
        self.assertEqual(created_post.user_id, self.user2_id)
        self.assertEqual(created_post.group, created_group)

        # Step 6: User1 sends a direct message to User2
        mock_jwt_decode.return_value = self.user1_payload
        message_data = {
            'recipient_id': self.user2_id,
            'content': 'Welcome to the group! Looking forward to your contributions.'
        }

        response = self.client.post(
            '/messages/',
            data=json.dumps(message_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        created_message = Message.objects.first()
        self.assertEqual(created_message.sender_id, self.user1_id)
        self.assertEqual(created_message.recipient_id, self.user2_id)

        # Step 7: User2 replies to the message
        mock_jwt_decode.return_value = self.user2_payload
        reply_data = {
            'recipient_id': self.user1_id,
            'content': 'Thank you! I am excited to contribute.'
        }

        response = self.client.post(
            '/messages/',
            data=json.dumps(reply_data),
            content_type='application/json',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 2)

    @patch('tweets.middleware.jwt.decode')
    def test_group_admin_workflow(self, mock_jwt_decode):
        """Test group admin workflow: create group, add members, manage posts."""

        # Step 1: User1 creates a group
        mock_jwt_decode.return_value = self.user1_payload
        group_data = {
            'name': 'Project Team',
            'description': 'Team collaboration space'
        }

        response = self.client.post(
            '/groups/',
            data=json.dumps(group_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        created_group = Group.objects.first()

        # Step 2: Admin adds User2 directly (without invite)
        add_member_data = {'user_id': self.user2_id}

        response = self.client.post(
            f'/groups/{created_group.id}/add-member/',
            data=json.dumps(add_member_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_group.refresh_from_db()
        self.assertIn(self.user2_id, created_group.members)

        # Step 3: Admin adds User3 directly
        add_member_data = {'user_id': self.user3_id}

        response = self.client.post(
            f'/groups/{created_group.id}/add-member/',
            data=json.dumps(add_member_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created_group.refresh_from_db()
        self.assertIn(self.user3_id, created_group.members)

        # Step 4: All members post in the group
        mock_jwt_decode.return_value = self.user2_payload
        response = self.client.post(
            f'/groups/{created_group.id}/posts/',
            data=json.dumps({'content': 'User2 post'}),
            content_type='application/json',
            **self._get_auth_headers(self.user2_id)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_jwt_decode.return_value = self.user3_payload
        response = self.client.post(
            f'/groups/{created_group.id}/posts/',
            data=json.dumps({'content': 'User3 post'}),
            content_type='application/json',
            **self._get_auth_headers(self.user3_id)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Step 5: Admin views all group posts
        mock_jwt_decode.return_value = self.user1_payload
        response = self.client.get(
            f'/groups/{created_group.id}/posts/',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    @patch('tweets.middleware.jwt.decode')
    def test_cross_app_data_consistency(self, mock_jwt_decode):
        """Test data consistency across tweets, groups, and messages."""

        # Create test data across all apps
        mock_jwt_decode.return_value = self.user1_payload

        # Create tweets
        for i in range(3):
            tweet_data = {'content': f'Tweet number {i+1}'}
            response = self.client.post(
                '/statuses/',
                data=json.dumps(tweet_data),
                content_type='application/json',
                **self._get_auth_headers(self.user1_id)
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create groups
        for i in range(2):
            group_data = {
                'name': f'Group {i+1}',
                'description': f'Description for group {i+1}'
            }
            response = self.client.post(
                '/groups/',
                data=json.dumps(group_data),
                content_type='application/json',
                **self._get_auth_headers(self.user1_id)
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create messages
        mock_jwt_decode.return_value = self.user2_payload
        for i in range(4):
            message_data = {
                'recipient_id': self.user1_id,
                'content': f'Message {i+1} to user1'
            }
            response = self.client.post(
                '/messages/',
                data=json.dumps(message_data),
                content_type='application/json',
                **self._get_auth_headers(self.user2_id)
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify data counts
        self.assertEqual(Tweets.objects.count(), 3)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(Message.objects.count(), 4)

        # Verify user associations
        user1_tweets = Tweets.objects.filter(user_id=self.user1_id)
        self.assertEqual(user1_tweets.count(), 3)

        user1_groups = Group.objects.filter(creator_id=self.user1_id)
        self.assertEqual(user1_groups.count(), 2)

        user1_messages_received = Message.objects.filter(recipient_id=self.user1_id)
        self.assertEqual(user1_messages_received.count(), 4)

    @patch('tweets.middleware.jwt.decode')
    def test_permission_boundaries(self, mock_jwt_decode):
        """Test that users can only access data they have permissions for."""

        # User1 creates a group
        mock_jwt_decode.return_value = self.user1_payload
        group_data = {'name': 'Private Group', 'description': 'Exclusive group'}

        response = self.client.post(
            '/groups/',
            data=json.dumps(group_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        private_group = Group.objects.first()

        # User2 (not a member) tries to view group posts
        mock_jwt_decode.return_value = self.user2_payload
        response = self.client.get(
            f'/groups/{private_group.id}/posts/',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # User2 tries to post in the group
        response = self.client.post(
            f'/groups/{private_group.id}/posts/',
            data=json.dumps({'content': 'Unauthorized post'}),
            content_type='application/json',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # User2 tries to invite someone to the group
        response = self.client.post(
            f'/groups/{private_group.id}/invite/',
            data=json.dumps({'invitee_id': self.user3_id}),
            content_type='application/json',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('tweets.middleware.jwt.decode')
    def test_messaging_privacy(self, mock_jwt_decode):
        """Test that users can only see messages addressed to them."""

        # User1 sends message to User2
        mock_jwt_decode.return_value = self.user1_payload
        message_data = {
            'recipient_id': self.user2_id,
            'content': 'Private message for User2'
        }

        response = self.client.post(
            '/messages/',
            data=json.dumps(message_data),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User2 can see the message
        mock_jwt_decode.return_value = self.user2_payload
        response = self.client.get(
            '/messages/',
            **self._get_auth_headers(self.user2_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Private message for User2')

        # User3 cannot see the message
        mock_jwt_decode.return_value = self.user3_payload
        response = self.client.get(
            '/messages/',
            **self._get_auth_headers(self.user3_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    @patch('tweets.middleware.jwt.decode')
    def test_global_timeline_access(self, mock_jwt_decode):
        """Test that all users can see all tweets (global timeline)."""

        # Multiple users create tweets
        mock_jwt_decode.return_value = self.user1_payload
        response = self.client.post(
            '/statuses/',
            data=json.dumps({'content': 'User1 tweet'}),
            content_type='application/json',
            **self._get_auth_headers(self.user1_id)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_jwt_decode.return_value = self.user2_payload
        response = self.client.post(
            '/statuses/',
            data=json.dumps({'content': 'User2 tweet'}),
            content_type='application/json',
            **self._get_auth_headers(self.user2_id)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User3 can see all tweets
        mock_jwt_decode.return_value = self.user3_payload
        response = self.client.get(
            '/statuses/',
            **self._get_auth_headers(self.user3_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        tweet_contents = [tweet['content'] for tweet in response.data]
        self.assertIn('User1 tweet', tweet_contents)
        self.assertIn('User2 tweet', tweet_contents)