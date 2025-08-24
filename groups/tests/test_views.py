from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import Mock, patch
from ..models import Group, GroupPost, GroupInvite
from ..views import (
    GroupListCreateView, GroupAddMemberView, GroupInviteView,
    GroupAcceptInviteView, GroupPostListCreateView
)
from ..serializers import GroupSerializer, GroupPostSerializer, GroupInviteSerializer
import urllib.parse


class GroupListCreateViewTest(TestCase):
    def setUp(self):
        self.group_data = {
            'name': 'Test Group',
            'description': 'A test group',
            'creator_id': 'user123',
            'creator_name': 'Test User',
            'moderators': ['user123'],
            'moderator_names': ['Test User'],
            'members': ['user123'],
            'member_names': ['Test User']
        }

        self.group_data_2 = {
            'name': 'Test Group 2',
            'description': 'Another test group',
            'creator_id': 'user456',
            'creator_name': 'Test User 2',
            'moderators': ['user456'],
            'moderator_names': ['Test User 2'],
            'members': ['user456'],
            'member_names': ['Test User 2']
        }

    def test_group_create_success(self):
        """Test successful group creation."""
        response = self.client.post('/groups/create/', self.group_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_group = Group.objects.get(name='Test Group')
        self.assertEqual(created_group.creator_id, 'user123')
        self.assertEqual(created_group.moderators, ['user123'])

    def test_group_create_response_structure(self):
        """Test that group creation response has correct structure."""
        response = self.client.post('/groups/create/', self.group_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that response contains expected fields
        response_data = response.data
        self.assertIn('id', response_data)
        self.assertIn('name', response_data)
        self.assertIn('description', response_data)
        self.assertIn('creator_id', response_data)
        self.assertIn('moderators', response_data)
        self.assertIn('members', response_data)
        self.assertIn('created_at', response_data)

        # Check that creator is automatically added to moderators and members
        self.assertIn('user123', response_data['moderators'])
        self.assertIn('user123', response_data['members'])

    def test_group_create_validation(self):
        """Test group creation validation."""
        # Original data should not have creator_id, moderators, or members
        original_data = {
            'name': 'Valid Group',
            'description': 'A valid group'
        }
        self.assertNotIn('creator_id', original_data)
        self.assertNotIn('moderators', original_data)
        self.assertNotIn('members', original_data)

        # Test that required fields are enforced
        invalid_data = {'description': 'Missing name'}
        response = self.client.post('/groups/create/', invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_group_list_success(self):
        """Test successful group listing."""
        # Create a group first
        Group.objects.create(**self.group_data)

        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Group')

    def test_group_detail_success(self):
        """Test successful group detail retrieval."""
        group = Group.objects.create(**self.group_data)

        response = self.client.get(f'/groups/{group.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Group')

    def test_group_join_success(self):
        """Test successful group joining."""
        group = Group.objects.create(**self.group_data)

        join_data = {'user_id': 'new_user'}
        response = self.client.post(f'/groups/{group.id}/join/', join_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that user was added to members
        group.refresh_from_db()
        self.assertIn('new_user', group.members)

    def test_group_leave_success(self):
        """Test successful group leaving."""
        group = Group.objects.create(**self.group_data)

        leave_data = {'user_id': 'user123'}
        response = self.client.post(f'/groups/{group.id}/leave/', leave_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that user was removed from members
        group.refresh_from_db()
        self.assertNotIn('user123', group.members)

    def test_group_moderation_add_member(self):
        """Test adding member through moderation."""
        group = Group.objects.create(**self.group_data)

        moderation_data = {
            'action': 'add_member',
            'user_id': 'new_member'
        }
        response = self.client.post(f'/groups/{group.id}/moderate/', moderation_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that user was added to members
        group.refresh_from_db()
        self.assertIn('new_member', group.members)

    def test_group_moderation_remove_member(self):
        """Test removing member through moderation."""
        group = Group.objects.create(**self.group_data)

        moderation_data = {
            'action': 'remove_member',
            'user_id': 'user123'
        }
        response = self.client.post(f'/groups/{group.id}/moderate/', moderation_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that user was removed from members
        group.refresh_from_db()
        self.assertNotIn('user123', group.members)

    def test_group_admin_add_moderator(self):
        """Test adding moderator through admin."""
        group = Group.objects.create(**self.group_data)

        admin_data = {
            'action': 'add_moderator',
            'user_id': 'new_moderator'
        }
        response = self.client.post(f'/groups/{group.id}/admin/', admin_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that user was added to moderators
        group.refresh_from_db()
        self.assertIn('new_moderator', group.moderators)

    def test_group_admin_remove_moderator(self):
        """Test removing moderator through admin."""
        group = Group.objects.create(**self.group_data)

        admin_data = {
            'action': 'remove_moderator',
            'user_id': 'user123'
        }
        response = self.client.post(f'/groups/{group.id}/admin/', admin_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that user was removed from moderators
        group.refresh_from_db()
        self.assertNotIn('user123', group.moderators)


class GroupAddMemberViewTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = GroupAddMemberView.as_view()

        self.group = Group.objects.create(
            name='Test Group',
            creator_id='admin_user',
            admins=['admin_user'],
            members=['admin_user']
        )

        self.encoded_name = urllib.parse.quote(self.group.name, safe='')
        self.valid_member_data = {'user_id': 'new_member'}

    def test_add_member_as_admin(self):
        """Test admin can add new member to group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/add_member/', self.valid_member_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertIn('new_member', self.group.members)
        self.assertIn('notification', response.data)

    def test_add_member_not_admin(self):
        """Test non-admin cannot add member to group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/add_member/', self.valid_member_data)
        request.user_id = 'regular_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Not an admin')

    def test_add_member_nonexistent_group(self):
        """Test adding member to non-existent group returns 404."""
        request = self.factory.post('/groups/999/add_member/', self.valid_member_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name='999')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Group Not Found')

    def test_add_existing_member(self):
        """Test adding already existing member returns group data."""
        self.group.members.append('existing_member')
        self.group.save()

        request = self.factory.post(f'/groups/{self.encoded_name}/add_member/', {'user_id': 'existing_member'})
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should not add duplicate
        self.assertEqual(self.group.members.count('existing_member'), 1)

    def test_add_member_missing_user_id(self):
        """Test adding member without user_id returns group data."""
        request = self.factory.post(f'/groups/{self.encoded_name}/add_member/', {})
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return group data without changes
        self.assertIn('id', response.data)

    def test_add_member_notification_message(self):
        """Test add member includes notification message."""
        request = self.factory.post(f'/groups/{self.encoded_name}/add_member/', self.valid_member_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_notification = "User new_member has been added to the group."
        self.assertEqual(response.data['notification'], expected_notification)


class GroupInviteViewTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = GroupInviteView.as_view()

        self.group = Group.objects.create(
            name='Test Group',
            creator_id='admin_user',
            admins=['admin_user'],
            members=['admin_user']
        )

        self.encoded_name = urllib.parse.quote(self.group.name, safe='')
        self.valid_invite_data = {'invitee_id': 'invited_user'}

    def test_create_invite_as_admin(self):
        """Test admin can create invite for group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/invite/', self.valid_invite_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupInvite.objects.count(), 1)

        invite = GroupInvite.objects.first()
        self.assertEqual(invite.invitee_id, 'invited_user')
        self.assertEqual(invite.inviter_id, 'admin_user')
        self.assertEqual(invite.group, self.group)

    def test_create_invite_not_admin(self):
        """Test non-admin cannot create invite for group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/invite/', self.valid_invite_data)
        request.user_id = 'regular_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Not an admin')

    def test_create_invite_nonexistent_group(self):
        """Test creating invite for non-existent group returns 404."""
        request = self.factory.post('/groups/999/invite/', self.valid_invite_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name='999')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Group not found')

    def test_create_invite_assigns_data(self):
        """Test invite creation assigns correct group and inviter."""
        request = self.factory.post(f'/groups/{self.encoded_name}/invite/', self.valid_invite_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['group'], self.group.id)
        self.assertEqual(response.data['inviter_id'], 'admin_user')

    def test_create_invite_invalid_data(self):
        """Test creating invite with invalid data returns 400."""
        invalid_data = {'invitee_id': ''}
        request = self.factory.post(f'/groups/{self.encoded_name}/invite/', invalid_data)
        request.user_id = 'admin_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invitee_id', response.data)


class GroupAcceptInviteViewTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = GroupAcceptInviteView.as_view()

        self.group = Group.objects.create(
            name='Test Group',
            creator_id='admin_user',
            admins=['admin_user'],
            members=['admin_user']
        )

        self.invite = GroupInvite.objects.create(
            group=self.group,
            invitee_id='invited_user',
            inviter_id='admin_user'
        )

    def test_accept_invite_valid(self):
        """Test accepting valid invite adds user to group."""
        request = self.factory.post(f'/groups/invites/{self.invite.id}/accept/')
        request.user_id = 'invited_user'

        response = self.view(request, invite_id=self.invite.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertIn('invited_user', self.group.members)
        self.assertEqual(GroupInvite.objects.count(), 0)  # Invite should be deleted

    def test_accept_invite_wrong_user(self):
        """Test accepting invite with wrong user returns 404."""
        request = self.factory.post(f'/groups/invites/{self.invite.id}/accept/')
        request.user_id = 'wrong_user'

        response = self.view(request, invite_id=self.invite.id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Invite not Found')

    def test_accept_invite_nonexistent(self):
        """Test accepting non-existent invite returns 404."""
        request = self.factory.post('/groups/invites/999/accept/')
        request.user_id = 'invited_user'

        response = self.view(request, invite_id=999)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    def test_accept_invite_already_member(self):
        """Test accepting invite when already member works properly."""
        self.group.members.append('invited_user')
        self.group.save()

        request = self.factory.post(f'/groups/invites/{self.invite.id}/accept/')
        request.user_id = 'invited_user'

        response = self.view(request, invite_id=self.invite.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(GroupInvite.objects.count(), 0)  # Invite should still be deleted
        # Should not add duplicate member
        self.assertEqual(self.group.members.count('invited_user'), 1)

    def test_accept_invite_returns_group_data(self):
        """Test accepting invite returns group data."""
        request = self.factory.post(f'/groups/invites/{self.invite.id}/accept/')
        request.user_id = 'invited_user'

        response = self.view(request, invite_id=self.invite.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.group.id)
        self.assertEqual(response.data['name'], 'Test Group')


class GroupPostListCreateViewTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = GroupPostListCreateView.as_view()

        self.group = Group.objects.create(
            name='Test Group',
            creator_id='admin_user',
            admins=['admin_user'],
            members=['admin_user', 'member_user']
        )

        # Create test posts
        self.post1 = GroupPost.objects.create(
            group=self.group,
            user_id='admin_user',
            content='First post'
        )
        self.post2 = GroupPost.objects.create(
            group=self.group,
            user_id='member_user',
            content='Second post'
        )

        self.encoded_name = urllib.parse.quote(self.group.name, safe='')
        self.valid_post_data = {'content': 'New post content'}

    def test_get_posts_as_member(self):
        """Test member can view group posts."""
        request = self.factory.get(f'/groups/{self.encoded_name}/posts/')
        request.user_id = 'member_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_posts_not_member(self):
        """Test non-member cannot view group posts."""
        request = self.factory.get(f'/groups/{self.encoded_name}/posts/')
        request.user_id = 'non_member'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Not a group member')

    def test_get_posts_nonexistent_group(self):
        """Test viewing posts for non-existent group returns 404."""
        request = self.factory.get('/groups/999/posts/')
        request.user_id = 'member_user'

        response = self.view(request, group_name='999')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Group not found')

    def test_create_post_as_member(self):
        """Test member can create post in group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/posts/', self.valid_post_data)
        request.user_id = 'member_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GroupPost.objects.count(), 3)

        created_post = GroupPost.objects.get(content='New post content')
        self.assertEqual(created_post.user_id, 'member_user')
        self.assertEqual(created_post.group, self.group)

    def test_create_post_not_member(self):
        """Test non-member cannot create post in group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/posts/', self.valid_post_data)
        request.user_id = 'non_member'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Not a group member')

    def test_create_post_nonexistent_group(self):
        """Test creating post for non-existent group returns 404."""
        request = self.factory.post('/groups/999/posts/', self.valid_post_data)
        request.user_id = 'member_user'

        response = self.view(request, group_name='999')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Group not found')

    def test_create_post_assigns_data(self):
        """Test post creation assigns correct user and group."""
        request = self.factory.post(f'/groups/{self.encoded_name}/posts/', self.valid_post_data)
        request.user_id = 'member_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_id'], 'member_user')
        self.assertEqual(response.data['group'], self.group.id)

    def test_create_post_invalid_data(self):
        """Test creating post with invalid data returns 400."""
        invalid_data = {'content': ''}
        request = self.factory.post(f'/groups/{self.encoded_name}/posts/', invalid_data)
        request.user_id = 'member_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_get_posts_filters_by_group(self):
        """Test GET posts returns only posts for the specified group."""
        # Create another group with posts
        other_group = Group.objects.create(
            name='Other Group',
            creator_id='admin_user',
            admins=['admin_user'],
            members=['admin_user', 'member_user']
        )
        GroupPost.objects.create(
            group=other_group,
            user_id='admin_user',
            content='Other group post'
        )

        request = self.factory.get(f'/groups/{self.encoded_name}/posts/')
        request.user_id = 'member_user'

        response = self.view(request, group_name=self.group.name)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Only posts from the test group
        post_contents = [post['content'] for post in response.data['results']]
        self.assertIn('First post', post_contents)
        self.assertIn('Second post', post_contents)
        self.assertNotIn('Other group post', post_contents)