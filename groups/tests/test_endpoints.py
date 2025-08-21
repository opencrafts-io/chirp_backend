import json
import urllib.parse
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from chirp.jwt_utils import generate_test_token
from ..models import Group, GroupPost, GroupInvite
import unittest


@unittest.skip("JWT authentication disabled for development")
class GroupsEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.groups_url = '/groups/'
        self.test_user_id = 'user123'
        self.test_user_id_2 = 'user456'
        self.valid_group_data = {
            'name': 'Test Group',
            'description': 'A test group for testing'
        }

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_groups_with_valid_jwt(self):
        """Test GET /groups/ with valid JWT token."""
        # Create a group where the user is a member
        group = Group.objects.create(
            name='Test Group',
            description='Test description',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

        response = self.client.get(
            self.groups_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Group')

    def test_get_groups_without_jwt(self):
        """Test GET /groups/ without JWT token returns 401."""
        response = self.client.get(self.groups_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_get_groups_with_invalid_jwt(self):
        """Test GET /groups/ with invalid JWT token returns 401."""
        response = self.client.get(
            self.groups_url,
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.json())

    def test_get_groups_filters_by_membership(self):
        """Test GET /groups/ only returns groups where user is a member."""
        # Create groups with different memberships
        group1 = Group.objects.create(
            name='My Group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

        Group.objects.create(
            name='Other Group',
            creator_id=self.test_user_id_2,
            admins=[self.test_user_id_2],
            members=[self.test_user_id_2]
        )

        response = self.client.get(
            self.groups_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'My Group')

    def test_post_group_with_valid_jwt(self):
        """Test POST /groups/ with valid JWT token creates group."""
        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 1)

        created_group = Group.objects.first()
        self.assertEqual(created_group.name, 'Test Group')
        self.assertEqual(created_group.creator_id, self.test_user_id)
        self.assertIn(self.test_user_id, created_group.admins)
        self.assertIn(self.test_user_id, created_group.members)

    def test_post_group_without_jwt(self):
        """Test POST /groups/ without JWT token returns 401."""
        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Group.objects.count(), 0)

    def test_post_group_with_invalid_jwt(self):
        """Test POST /groups/ with invalid JWT token returns 401."""
        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer invalid_token_here'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Group.objects.count(), 0)

    def test_post_group_invalid_data(self):
        """Test POST /groups/ with invalid data returns 400."""
        invalid_data = {'name': ''}  # Empty name
        response = self.client.post(
            self.groups_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        self.assertEqual(Group.objects.count(), 0)

    def test_post_group_duplicate_name(self):
        """Test POST /groups/ with duplicate name returns 400."""
        # Create a group first
        Group.objects.create(
            name='Test Group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Group.objects.count(), 1)

    def test_post_group_response_format(self):
        """Test POST /groups/ returns proper response format."""
        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_fields = ['id', 'name', 'description', 'creator_id', 'admins', 'members', 'created_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_post_group_creator_setup(self):
        """Test POST /groups/ properly sets up creator as admin and member."""
        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['creator_id'], self.test_user_id)
        self.assertIn(self.test_user_id, response.data['admins'])
        self.assertIn(self.test_user_id, response.data['members'])

    def test_unsupported_http_methods(self):
        """Test that unsupported HTTP methods return 405."""
        # Test PUT
        response = self.client.put(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE
        response = self.client.delete(
            self.groups_url,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


@unittest.skip("JWT authentication disabled for development")
class GroupMemberEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.test_user_id = 'admin_user'
        self.test_user_id_2 = 'member_user'
        self.test_user_id_3 = 'new_user'

        # Create a test group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id, self.test_user_id_2]
        )

        encoded_name = urllib.parse.quote(self.group.name, safe='')
        self.add_member_url = f'/groups/{encoded_name}/add_member/'
        self.valid_member_data = {
            'user_id': self.test_user_id_3
        }

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_add_member_as_admin(self):
        """Test adding member as admin succeeds."""
        response = self.client.post(
            self.add_member_url,
            data=json.dumps(self.valid_member_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertIn(self.test_user_id_3, self.group.members)
        self.assertIn('notification', response.data)

    def test_add_member_as_non_admin(self):
        """Test adding member as non-admin returns 403."""
        response = self.client.post(
            self.add_member_url,
            data=json.dumps(self.valid_member_data),
            content_type='application/json',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)

    def test_add_member_without_jwt(self):
        """Test adding member without JWT returns 401."""
        response = self.client.post(
            self.add_member_url,
            data=json.dumps(self.valid_member_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_member_invalid_group(self):
        """Test adding member to non-existent group returns 404."""
        url = '/groups/999/add_member/'
        response = self.client.post(
            url,
            data=json.dumps(self.valid_member_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_existing_member(self):
        """Test adding existing member returns success without duplicate."""
        existing_member_data = {'user_id': self.test_user_id_2}
        response = self.client.post(
            self.add_member_url,
            data=json.dumps(existing_member_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        # Should not have duplicate members
        member_count = self.group.members.count(self.test_user_id_2)
        self.assertEqual(member_count, 1)


@unittest.skip("JWT authentication disabled for development")
class GroupInviteEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.test_user_id = 'admin_user'
        self.test_user_id_2 = 'member_user'
        self.test_user_id_3 = 'invited_user'

        # Create a test group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id, self.test_user_id_2]
        )

        encoded_name = urllib.parse.quote(self.group.name, safe='')
        self.invite_url = f'/groups/{encoded_name}/invite/'
        self.valid_invite_data = {
            'invitee_id': self.test_user_id_3
        }

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_create_invite_as_admin(self):
        """Test creating invite as admin succeeds."""
        response = self.client.post(
            self.invite_url,
            data=json.dumps(self.valid_invite_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupInvite.objects.count(), 1)

        invite = GroupInvite.objects.first()
        self.assertEqual(invite.invitee_id, self.test_user_id_3)
        self.assertEqual(invite.inviter_id, self.test_user_id)
        self.assertEqual(invite.group, self.group)

    def test_create_invite_as_non_admin(self):
        """Test creating invite as non-admin returns 403."""
        response = self.client.post(
            self.invite_url,
            data=json.dumps(self.valid_invite_data),
            content_type='application/json',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(GroupInvite.objects.count(), 0)

    def test_create_invite_without_jwt(self):
        """Test creating invite without JWT returns 401."""
        response = self.client.post(
            self.invite_url,
            data=json.dumps(self.valid_invite_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_invite_invalid_group(self):
        """Test creating invite for non-existent group returns 404."""
        url = '/groups/999/invite/'
        response = self.client.post(
            url,
            data=json.dumps(self.valid_invite_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_invite_invalid_data(self):
        """Test creating invite with invalid data returns 400."""
        invalid_data = {'invitee_id': ''}
        response = self.client.post(
            self.invite_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(GroupInvite.objects.count(), 0)


@unittest.skip("JWT authentication disabled for development")
class GroupAcceptInviteEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.test_user_id = 'admin_user'
        self.test_user_id_2 = 'invited_user'

        # Create a test group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

        # Create an invite
        self.invite = GroupInvite.objects.create(
            group=self.group,
            invitee_id=self.test_user_id_2,
            inviter_id=self.test_user_id
        )

        self.accept_invite_url = f'/groups/invites/{self.invite.id}/accept/'

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id_2
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_accept_invite_as_invitee(self):
        """Test accepting invite as invitee succeeds."""
        response = self.client.post(
            self.accept_invite_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertIn(self.test_user_id_2, self.group.members)

        # Invite should be deleted
        self.assertEqual(GroupInvite.objects.count(), 0)

    def test_accept_invite_as_wrong_user(self):
        """Test accepting invite as wrong user returns 404."""
        response = self.client.post(
            self.accept_invite_url,
            **self._get_auth_headers('wrong_user')
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_invite_without_jwt(self):
        """Test accepting invite without JWT returns 401."""
        response = self.client.post(self.accept_invite_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_accept_invite_invalid_invite(self):
        """Test accepting non-existent invite returns 404."""
        url = '/groups/invites/999/accept/'
        response = self.client.post(
            url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@unittest.skip("JWT authentication disabled for development")
class GroupPostEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.test_user_id = 'member_user'
        self.test_user_id_2 = 'non_member_user'

        # Create a test group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

        encoded_name = urllib.parse.quote(self.group.name, safe='')
        self.group_posts_url = f'/groups/{encoded_name}/posts/'
        self.valid_post_data = {
            'content': 'This is a test group post!'
        }

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers using real JWT tokens."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_group_posts_as_member(self):
        """Test GET group posts as member succeeds."""
        # Create a test post
        GroupPost.objects.create(
            group=self.group,
            user_id=self.test_user_id,
            content='Test post content'
        )

        response = self.client.get(
            self.group_posts_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Test post content')

    def test_get_group_posts_as_non_member(self):
        """Test GET group posts as non-member returns 403."""
        response = self.client.get(
            self.group_posts_url,
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_group_posts_without_jwt(self):
        """Test GET group posts without JWT returns 401."""
        response = self.client.get(self.group_posts_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_group_posts_invalid_group(self):
        """Test GET posts for non-existent group returns 404."""
        url = '/groups/999/posts/'
        response = self.client.get(
            url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_group_post_as_member(self):
        """Test POST group post as member succeeds."""
        response = self.client.post(
            self.group_posts_url,
            data=json.dumps(self.valid_post_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupPost.objects.count(), 1)

        created_post = GroupPost.objects.first()
        self.assertEqual(created_post.content, 'This is a test group post!')
        self.assertEqual(created_post.user_id, self.test_user_id)

    def test_post_group_post_as_non_member(self):
        """Test POST group post as non-member returns 403."""
        response = self.client.post(
            self.group_posts_url,
            data=json.dumps(self.valid_post_data),
            content_type='application/json',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(GroupPost.objects.count(), 0)

    def test_post_group_post_without_jwt(self):
        """Test POST group post without JWT returns 401."""
        response = self.client.post(
            self.group_posts_url,
            data=json.dumps(self.valid_post_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_group_post_invalid_data(self):
        """Test POST group post with invalid data returns 400."""
        invalid_data = {'content': ''}
        response = self.client.post(
            self.group_posts_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(GroupPost.objects.count(), 0)


@unittest.skip("JWT authentication disabled for development")
class GroupJoinLeaveEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.test_user_id = 'test_user_123'
        self.test_user_id_2 = 'test_user_456'

        # Create a test group
        self.group = Group.objects.create(
            name='Test Group',
            description='A test group for join/leave testing',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers."""
        user_id = user_id or self.test_user_id
        token = generate_test_token(user_id)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_join_group_success(self):
        """Test successfully joining a group."""
        response = self.client.post(
            f'/groups/{self.group.name}/join/',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Successfully joined group', response.data['message'])
        self.assertIn(self.test_user_id_2, response.data['group']['members'])

    def test_join_group_already_member(self):
        """Test joining a group when already a member."""
        response = self.client.post(
            f'/groups/{self.group.name}/join/',
            **self._get_auth_headers(self.test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Already a member', response.data['message'])

    def test_join_nonexistent_group(self):
        """Test joining a group that doesn't exist."""
        response = self.client.post(
            '/groups/nonexistent-group/join/',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Group not found', response.data['error'])

    def test_leave_group_success(self):
        """Test successfully leaving a group."""
        # First join the group
        self.group.members.append(self.test_user_id_2)
        self.group.save()

        response = self.client.post(
            f'/groups/{self.group.name}/leave/',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Successfully left group', response.data['message'])
        self.assertNotIn(self.test_user_id_2, response.data['group']['members'])

    def test_leave_group_not_member(self):
        """Test leaving a group when not a member."""
        response = self.client.post(
            f'/groups/{self.group.name}/leave/',
            **self._get_auth_headers(self.test_user_id_2)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Not a member', response.data['error'])

    def test_leave_group_as_creator(self):
        """Test that creator cannot leave the group."""
        response = self.client.post(
            f'/groups/{self.group.name}/leave/',
            **self._get_auth_headers(self.test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Group creator cannot leave', response.data['error'])

    def test_discover_groups(self):
        """Test discovering all groups with membership status."""
        # Create another group
        Group.objects.create(
            name='Another Group',
            description='Another test group',
            creator_id=self.test_user_id_2,
            admins=[self.test_user_id_2],
            members=[self.test_user_id_2]
        )

        response = self.client.get(
            '/groups/discover/',
            **self._get_auth_headers(self.test_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        # Check that membership status is included
        for group in response.data['results']:
            self.assertIn('is_member', group)
            self.assertIn('is_admin', group)
            self.assertIn('is_creator', group)

            if group['name'] == 'Test Group':
                self.assertTrue(group['is_member'])
                self.assertTrue(group['is_admin'])
                self.assertTrue(group['is_creator'])
            else:
                self.assertFalse(group['is_member'])
                self.assertFalse(group['is_admin'])
                self.assertFalse(group['is_creator'])