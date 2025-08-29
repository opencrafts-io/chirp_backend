from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from groups.models import Group, GroupPost, GroupInvite, InviteLink
from unittest.mock import patch


class GroupDeletionTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.creator_id = "creator-123"
        self.creator_name = "Test Creator"
        self.moderator_id = "moderator-456"
        self.moderator_name = "Test Moderator"
        self.member_id = "member-789"
        self.member_name = "Test Member"

        # Create a test group with a unique ID
        self.group = Group.objects.create(
            id=999,  # Use a unique ID to avoid conflicts
            name="Test Group",
            description="A test group for deletion testing",
            creator_id=self.creator_id,
            creator_name=self.creator_name,
            moderators=[self.creator_id, self.moderator_id],
            moderator_names=[self.creator_name, self.moderator_name],
            members=[self.creator_id, self.moderator_id, self.member_id],
            member_names=[self.creator_name, self.moderator_name, self.member_name],
            is_private=False
        )

        # Create related data
        self.group_post = GroupPost.objects.create(
            group=self.group,
            user_id=self.creator_id,
            content="Test post content"
        )

        self.group_invite = GroupInvite.objects.create(
            group=self.group,
            invitee_id="invitee-123",
            inviter_id=self.creator_id
        )

        self.invite_link = InviteLink.objects.create(
            group=self.group,
            created_by=self.creator_id,
            created_by_name=self.creator_name,
            token="test-token-123",
            expiration_hours=72
        )

        # Create API client
        self.client = APIClient()

    def test_creator_can_delete_group(self):
        """Test that group creator can delete the group"""
        # Make DELETE request with creator user_id
        url = f"{reverse('group-delete', kwargs={'group_id': self.group.id})}?user_id={self.creator_id}"
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('deleted_group_id', response.data)

        # Verify group is deleted
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())

        # Verify related data is also deleted (due to CASCADE)
        self.assertFalse(GroupPost.objects.filter(id=self.group_post.id).exists())
        self.assertFalse(GroupInvite.objects.filter(id=self.group_invite.id).exists())
        self.assertFalse(InviteLink.objects.filter(id=self.invite_link.id).exists())

    def test_moderator_cannot_delete_group(self):
        """Test that moderators cannot delete the group"""
        # Make DELETE request with moderator user_id
        url = f"{reverse('group-delete', kwargs={'group_id': self.group.id})}?user_id={self.moderator_id}"
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('Only the group creator can delete this group', response.data['error'])

        # Verify group still exists
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())

    def test_member_cannot_delete_group(self):
        """Test that regular members cannot delete the group"""
        # Make DELETE request with member user_id
        url = f"{reverse('group-delete', kwargs={'group_id': self.group.id})}?user_id={self.member_id}"
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('Only the group creator can delete this group', response.data['error'])

        # Verify group still exists
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())

    def test_unauthorized_user_cannot_delete_group(self):
        """Test that unauthorized users cannot delete the group"""
        # Make DELETE request with unauthorized user_id
        url = f"{reverse('group-delete', kwargs={'group_id': self.group.id})}?user_id=unauthorized-123"
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('Only the group creator can delete this group', response.data['error'])

        # Verify group still exists
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())

    def test_delete_nonexistent_group(self):
        """Test deleting a group that doesn't exist"""
        # Make DELETE request to non-existent group with creator user_id
        url = f"{reverse('group-delete', kwargs={'group_id': 99999})}?user_id={self.creator_id}"
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('Group not found', response.data['error'])

    def test_delete_group_without_user_id_parameter(self):
        """Test deleting a group without user_id parameter"""
        # Make DELETE request without user_id parameter
        url = reverse('group-delete', kwargs={'group_id': self.group.id})
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('user_id query parameter is required', response.data['error'])

        # Verify group still exists
        self.assertTrue(Group.objects.filter(id=self.group.id).exists())

    def test_cascade_deletion(self):
        """Test that related data is properly deleted when group is deleted"""
        # Make DELETE request with creator user_id
        url = f"{reverse('group-delete', kwargs={'group_id': self.group.id})}?user_id={self.creator_id}"
        response = self.client.delete(url)

        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all related data is deleted
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())
        self.assertFalse(GroupPost.objects.filter(group_id=self.group.id).exists())
        self.assertFalse(GroupInvite.objects.filter(group_id=self.group.id).exists())
        self.assertFalse(InviteLink.objects.filter(group_id=self.group.id).exists())

    def test_admin_can_delete_group_from_admin_interface(self):
        """Test that Django admin configuration allows group deletion"""
        # Create a new group specifically for this test
        admin_test_group = Group.objects.create(
            id=888,  # Use a different ID
            name="Admin Test Group",
            description="A test group for admin deletion testing",
            creator_id=self.creator_id,
            creator_name=self.creator_name,
            moderators=[self.creator_id],
            moderator_names=[self.creator_name],
            members=[self.creator_id],
            member_names=[self.creator_name],
            is_private=False
        )

        # Test that the admin configuration allows deletion
        from groups.admin import GroupAdmin
        from django.contrib import admin
        admin_instance = GroupAdmin(Group, admin.site)

        # Verify that has_delete_permission returns True
        self.assertTrue(admin_instance.has_delete_permission(None))

        # Verify the group exists
        self.assertTrue(Group.objects.filter(id=admin_test_group.id).exists())
