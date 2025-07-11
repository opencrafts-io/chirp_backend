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
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = GroupListCreateView.as_view()

        # Create test groups
        self.group1 = Group.objects.create(
            name='Group 1',
            creator_id='user123',
            admins=['user123'],
            members=['user123', 'user456']
        )
        self.group2 = Group.objects.create(
            name='Group 2',
            creator_id='user456',
            admins=['user456'],
            members=['user456']
        )

        self.valid_group_data = {
            'name': 'New Group',
            'description': 'A new test group'
        }

    def test_get_groups_for_member(self):
        """Test GET request returns only groups where user is a member."""
        request = self.factory.get('/groups/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Group 1')

    def test_get_groups_no_membership(self):
        """Test GET request returns empty list for user with no memberships."""
        request = self.factory.get('/groups/')
        request.user_id = 'user_not_member'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_groups_multiple_memberships(self):
        """Test GET request returns all groups where user is a member."""
        # Add user123 to group2
        self.group2.members.append('user123')
        self.group2.save()

        request = self.factory.get('/groups/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_post_create_group_valid_data(self):
        """Test POST request creates group with valid data."""
        request = self.factory.post('/groups/', self.valid_group_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 3)  # 2 existing + 1 new

        created_group = Group.objects.get(name='New Group')
        self.assertEqual(created_group.creator_id, 'user123')
        self.assertEqual(created_group.admins, ['user123'])
        self.assertEqual(created_group.members, ['user123'])

    def test_post_create_group_assigns_creator_fields(self):
        """Test POST request assigns creator as admin and member."""
        request = self.factory.post('/groups/', self.valid_group_data)
        request.user_id = 'creator_user'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['creator_id'], 'creator_user')
        self.assertEqual(response.data['admins'], ['creator_user'])
        self.assertEqual(response.data['members'], ['creator_user'])

    def test_post_create_group_invalid_data(self):
        """Test POST request with invalid data returns 400."""
        invalid_data = {'name': '', 'description': 'No name'}
        request = self.factory.post('/groups/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_post_create_group_duplicate_name(self):
        """Test POST request with duplicate group name fails."""
        duplicate_data = {'name': 'Group 1', 'description': 'Duplicate name'}
        request = self.factory.post('/groups/', duplicate_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_modifies_data_copy(self):
        """Test POST request modifies copy of data, not original."""
        original_data = self.valid_group_data.copy()
        request = self.factory.post('/groups/', original_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Original data should not have creator_id, admins, or members
        self.assertNotIn('creator_id', original_data)
        self.assertNotIn('admins', original_data)
        self.assertNotIn('members', original_data)


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
        self.assertEqual(len(response.data), 2)

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
        self.assertEqual(len(response.data), 2)  # Only posts from the test group
        post_contents = [post['content'] for post in response.data]
        self.assertIn('First post', post_contents)
        self.assertIn('Second post', post_contents)
        self.assertNotIn('Other group post', post_contents)