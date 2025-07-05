import json
import jwt
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from ..models import Group, GroupPost, GroupInvite


class GroupsEndpointTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.client = APIClient()
        self.groups_url = '/groups/'
        self.test_user_id = 'user123'
        self.admin_user_id = 'admin456'

        # Create test groups
        self.group1 = Group.objects.create(
            name='Test Group 1',
            description='First test group',
            creator_id=self.admin_user_id,
            admins=[self.admin_user_id],
            members=[self.admin_user_id, self.test_user_id]
        )

        self.group2 = Group.objects.create(
            name='Test Group 2',
            description='Second test group',
            creator_id=self.test_user_id,
            admins=[self.test_user_id],
            members=[self.test_user_id]
        )

        # Mock JWT payload
        self.mock_jwt_payload = {
            'sub': self.test_user_id,
            'exp': 9999999999
        }

        self.valid_group_data = {
            'name': 'New Group',
            'description': 'A new test group'
        }

    def _create_mock_jwt_token(self, user_id=None):
        """Helper method to create a mock JWT token."""
        payload = self.mock_jwt_payload.copy()
        if user_id:
            payload['sub'] = user_id
        return jwt.encode(payload, 'mock_secret', algorithm='HS256')

    def _get_auth_headers(self, user_id=None):
        """Helper method to get authentication headers."""
        token = self._create_mock_jwt_token(user_id)
        return {'Authorization': f'Bearer {token}'}

    # GET /groups/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_get_groups_with_valid_jwt(self, mock_jwt_decode):
        """Test GET /groups/ with valid JWT token."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.groups_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # user123 is member of both groups

    @patch('tweets.middleware.jwt.decode')
    def test_get_groups_member_filtering(self, mock_jwt_decode):
        """Test GET /groups/ returns only groups where user is member."""
        mock_jwt_payload = {'sub': self.admin_user_id}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.get(
            self.groups_url,
            **self._get_auth_headers(self.admin_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # admin456 is only member of group1
        self.assertEqual(response.data[0]['name'], 'Test Group 1')

    def test_get_groups_without_jwt(self):
        """Test GET /groups/ without JWT token returns 401."""
        response = self.client.get(self.groups_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # POST /groups/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_post_create_group_with_valid_jwt(self, mock_jwt_decode):
        """Test POST /groups/ with valid JWT token creates group."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 3)

        created_group = Group.objects.get(name='New Group')
        self.assertEqual(created_group.creator_id, self.test_user_id)
        self.assertEqual(created_group.admins, [self.test_user_id])
        self.assertEqual(created_group.members, [self.test_user_id])

    @patch('tweets.middleware.jwt.decode')
    def test_post_create_group_invalid_data(self, mock_jwt_decode):
        """Test POST /groups/ with invalid data returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'name': '', 'description': 'No name'}
        response = self.client.post(
            self.groups_url,
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_post_create_group_duplicate_name(self, mock_jwt_decode):
        """Test POST /groups/ with duplicate name returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        duplicate_data = {'name': 'Test Group 1', 'description': 'Duplicate'}
        response = self.client.post(
            self.groups_url,
            data=json.dumps(duplicate_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # POST /groups/{id}/add-member/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_add_member_as_admin(self, mock_jwt_decode):
        """Test POST /groups/{id}/add-member/ as admin."""
        mock_jwt_payload = {'sub': self.admin_user_id}
        mock_jwt_decode.return_value = mock_jwt_payload

        member_data = {'user_id': 'new_member'}
        response = self.client.post(
            f'/groups/{self.group1.id}/add-member/',
            data=json.dumps(member_data),
            content_type='application/json',
            **self._get_auth_headers(self.admin_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group1.refresh_from_db()
        self.assertIn('new_member', self.group1.members)
        self.assertIn('notification', response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_add_member_not_admin(self, mock_jwt_decode):
        """Test POST /groups/{id}/add-member/ as non-admin returns 403."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        member_data = {'user_id': 'new_member'}
        response = self.client.post(
            f'/groups/{self.group1.id}/add-member/',
            data=json.dumps(member_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Not an admin')

    @patch('tweets.middleware.jwt.decode')
    def test_add_member_nonexistent_group(self, mock_jwt_decode):
        """Test POST /groups/{id}/add-member/ for non-existent group returns 404."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        member_data = {'user_id': 'new_member'}
        response = self.client.post(
            '/groups/999/add-member/',
            data=json.dumps(member_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Group Not Found')

    # POST /groups/{id}/invite/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_create_invite_as_admin(self, mock_jwt_decode):
        """Test POST /groups/{id}/invite/ as admin."""
        mock_jwt_payload = {'sub': self.admin_user_id}
        mock_jwt_decode.return_value = mock_jwt_payload

        invite_data = {'invitee_id': 'invited_user'}
        response = self.client.post(
            f'/groups/{self.group1.id}/invite/',
            data=json.dumps(invite_data),
            content_type='application/json',
            **self._get_auth_headers(self.admin_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupInvite.objects.count(), 1)

        invite = GroupInvite.objects.first()
        self.assertEqual(invite.invitee_id, 'invited_user')
        self.assertEqual(invite.inviter_id, self.admin_user_id)

    @patch('tweets.middleware.jwt.decode')
    def test_create_invite_not_admin(self, mock_jwt_decode):
        """Test POST /groups/{id}/invite/ as non-admin returns 403."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invite_data = {'invitee_id': 'invited_user'}
        response = self.client.post(
            f'/groups/{self.group1.id}/invite/',
            data=json.dumps(invite_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Not an admin')

    # POST /groups/invites/{id}/accept/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_accept_invite_valid(self, mock_jwt_decode):
        """Test POST /groups/invites/{id}/accept/ with valid invite."""
        invite = GroupInvite.objects.create(
            group=self.group1,
            invitee_id='invited_user',
            inviter_id=self.admin_user_id
        )

        mock_jwt_payload = {'sub': 'invited_user'}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.post(
            f'/groups/invites/{invite.id}/accept/',
            **self._get_auth_headers('invited_user')
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group1.refresh_from_db()
        self.assertIn('invited_user', self.group1.members)
        self.assertEqual(GroupInvite.objects.count(), 0)

    @patch('tweets.middleware.jwt.decode')
    def test_accept_invite_wrong_user(self, mock_jwt_decode):
        """Test POST /groups/invites/{id}/accept/ with wrong user returns 404."""
        invite = GroupInvite.objects.create(
            group=self.group1,
            invitee_id='invited_user',
            inviter_id=self.admin_user_id
        )

        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.post(
            f'/groups/invites/{invite.id}/accept/',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Invite not Found')

    # GET /groups/{id}/posts/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_get_group_posts_as_member(self, mock_jwt_decode):
        """Test GET /groups/{id}/posts/ as group member."""
        # Create test posts
        GroupPost.objects.create(
            group=self.group1,
            user_id=self.admin_user_id,
            content='First post'
        )
        GroupPost.objects.create(
            group=self.group1,
            user_id=self.test_user_id,
            content='Second post'
        )

        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            f'/groups/{self.group1.id}/posts/',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    @patch('tweets.middleware.jwt.decode')
    def test_get_group_posts_not_member(self, mock_jwt_decode):
        """Test GET /groups/{id}/posts/ as non-member returns 403."""
        mock_jwt_payload = {'sub': 'non_member'}
        mock_jwt_decode.return_value = mock_jwt_payload

        response = self.client.get(
            f'/groups/{self.group1.id}/posts/',
            **self._get_auth_headers('non_member')
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Not a group member')

    # POST /groups/{id}/posts/ tests
    @patch('tweets.middleware.jwt.decode')
    def test_create_group_post_as_member(self, mock_jwt_decode):
        """Test POST /groups/{id}/posts/ as group member."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        post_data = {'content': 'New group post'}
        response = self.client.post(
            f'/groups/{self.group1.id}/posts/',
            data=json.dumps(post_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupPost.objects.count(), 1)

        created_post = GroupPost.objects.first()
        self.assertEqual(created_post.content, 'New group post')
        self.assertEqual(created_post.user_id, self.test_user_id)

    @patch('tweets.middleware.jwt.decode')
    def test_create_group_post_not_member(self, mock_jwt_decode):
        """Test POST /groups/{id}/posts/ as non-member returns 403."""
        mock_jwt_payload = {'sub': 'non_member'}
        mock_jwt_decode.return_value = mock_jwt_payload

        post_data = {'content': 'New group post'}
        response = self.client.post(
            f'/groups/{self.group1.id}/posts/',
            data=json.dumps(post_data),
            content_type='application/json',
            **self._get_auth_headers('non_member')
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Not a group member')

    @patch('tweets.middleware.jwt.decode')
    def test_create_group_post_invalid_data(self, mock_jwt_decode):
        """Test POST /groups/{id}/posts/ with invalid data returns 400."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        invalid_data = {'content': ''}
        response = self.client.post(
            f'/groups/{self.group1.id}/posts/',
            data=json.dumps(invalid_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    # HTTP Method validation tests
    @patch('tweets.middleware.jwt.decode')
    def test_unsupported_http_methods(self, mock_jwt_decode):
        """Test unsupported HTTP methods return 405."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        # Test PUT on groups
        response = self.client.put(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE on groups
        response = self.client.delete(
            self.groups_url,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # Response format validation tests
    @patch('tweets.middleware.jwt.decode')
    def test_group_response_format(self, mock_jwt_decode):
        """Test group response contains expected fields."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        response = self.client.get(
            self.groups_url,
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        group_data = response.data[0]
        expected_fields = ['id', 'name', 'description', 'creator_id', 'admins', 'members', 'created_at']
        for field in expected_fields:
            self.assertIn(field, group_data)

    @patch('tweets.middleware.jwt.decode')
    def test_group_post_response_format(self, mock_jwt_decode):
        """Test group post response contains expected fields."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        post_data = {'content': 'Test post'}
        response = self.client.post(
            f'/groups/{self.group1.id}/posts/',
            data=json.dumps(post_data),
            content_type='application/json',
            **self._get_auth_headers()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        expected_fields = ['id', 'group', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    @patch('tweets.middleware.jwt.decode')
    def test_group_invite_response_format(self, mock_jwt_decode):
        """Test group invite response contains expected fields."""
        mock_jwt_payload = {'sub': self.admin_user_id}
        mock_jwt_decode.return_value = mock_jwt_payload

        invite_data = {'invitee_id': 'invited_user'}
        response = self.client.post(
            f'/groups/{self.group1.id}/invite/',
            data=json.dumps(invite_data),
            content_type='application/json',
            **self._get_auth_headers(self.admin_user_id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        expected_fields = ['id', 'group', 'invitee_id', 'inviter_id', 'created_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    # Content type handling tests
    @patch('tweets.middleware.jwt.decode')
    def test_content_type_handling(self, mock_jwt_decode):
        """Test different content types are handled properly."""
        mock_jwt_decode.return_value = self.mock_jwt_payload

        # Test form data
        response = self.client.post(
            self.groups_url,
            data=self.valid_group_data,
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test JSON data
        response = self.client.post(
            self.groups_url,
            data=json.dumps(self.valid_group_data),
            content_type='application/json',
            **self._get_auth_headers()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)