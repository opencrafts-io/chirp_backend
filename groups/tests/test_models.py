from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from groups.models import Group, GroupPost, GroupInvite


class GroupModelTest(TestCase):
    def setUp(self):
        self.valid_group_data = {
            'name': 'Test Group',
            'description': 'A test group',
            'creator_id': 'user123',
            'creator_name': 'Test User',
            'moderators': ['user123'],
            'moderator_names': ['Test User'],
            'members': ['user123'],
            'member_names': ['Test User']
        }

    def test_create_valid_group(self):
        """Test creating a valid group with all required fields."""
        group = Group.objects.create(**self.valid_group_data)

        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.description, 'A test group')
        self.assertEqual(group.creator_id, 'user123')
        self.assertEqual(group.moderators, ['user123'])
        self.assertEqual(group.members, ['user123'])
        self.assertIsNotNone(group.created_at)
        self.assertIsNotNone(group.id)

    def test_group_string_representation(self):
        """Test the __str__ method returns group name."""
        group = Group.objects.create(**self.valid_group_data)
        self.assertEqual(str(group), 'Test Group')

    def test_group_name_uniqueness(self):
        """Test that group names must be unique."""
        Group.objects.create(**self.valid_group_data)

        # Try to create another group with the same name
        duplicate_data = self.valid_group_data.copy()
        duplicate_data['creator_id'] = 'user456'

        with self.assertRaises(Exception):  # Should raise IntegrityError
            Group.objects.create(**duplicate_data)

    def test_group_name_max_length(self):
        """Test group name respects 100 character limit."""
        long_name = 'a' * 101
        group_data = self.valid_group_data.copy()
        group_data['name'] = long_name

        with self.assertRaises(Exception):
            Group.objects.create(**group_data)

    def test_group_empty_name(self):
        """Test that empty group name is not allowed."""
        group_data = self.valid_group_data.copy()
        group_data['name'] = ''

        group = Group(**group_data)
        with self.assertRaises(ValidationError):
            group.full_clean()

    def test_group_description_can_be_blank(self):
        """Test that group description can be blank."""
        group_data = self.valid_group_data.copy()
        group_data['description'] = ''

        group = Group.objects.create(**group_data)
        self.assertEqual(group.description, '')

    def test_group_json_fields_default_to_list(self):
        """Test that moderators and members default to empty lists."""
        group = Group.objects.create(
            name='Minimal Group',
            creator_id='user123',
            creator_name='Test User'
        )

        self.assertEqual(group.moderators, [])
        self.assertEqual(group.members, [])
        self.assertEqual(group.banned_users, [])
        self.assertEqual(group.rules, [])

    def test_group_json_fields_handle_lists(self):
        """Test that moderators and members handle list data properly."""
        group_data = self.valid_group_data.copy()
        group_data['moderators'] = ['user1', 'user2']
        group_data['moderator_names'] = ['User1', 'User2']
        group_data['members'] = ['user1', 'user2', 'user3']
        group_data['member_names'] = ['User1', 'User2', 'User3']

        group = Group.objects.create(**group_data)

        self.assertEqual(group.moderators, ['user1', 'user2'])
        self.assertEqual(group.members, ['user1', 'user2', 'user3'])

    def test_group_auto_timestamp(self):
        """Test that created_at is automatically set."""
        group = Group.objects.create(**self.valid_group_data)
        self.assertIsNotNone(group.created_at)


class GroupPostModelTest(TestCase):
    def setUp(self):
        # Create a group without specifying ID to avoid conflicts
        self.group = Group.objects.create(
            name='Test Group for Posts',
            description='A test group for posts',
            creator_id='user123',
            creator_name='Test User',
            moderators=['user123'],
            moderator_names=['Test User'],
            members=['user123'],
            member_names=['Test User']
        )

        self.valid_post_data = {
            'content': 'This is a test post!',
            'user_id': 'user123',
            'group': self.group
        }

    def test_create_valid_group_post(self):
        """Test creating a valid group post with all required fields."""
        post = GroupPost.objects.create(**self.valid_post_data)

        self.assertEqual(post.content, 'This is a test post!')
        self.assertEqual(post.user_id, 'user123')
        self.assertEqual(post.group, self.group)
        self.assertIsNotNone(post.created_at)

    def test_group_post_auto_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        post = GroupPost.objects.create(**self.valid_post_data)

        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)

        # Update the post
        post.content = 'Updated content'
        post.save()

        self.assertGreater(post.updated_at, post.created_at)

    def test_group_post_cascade_delete(self):
        """Test that posts are deleted when group is deleted."""
        post = GroupPost.objects.create(**self.valid_post_data)
        post_id = post.id

        # Delete the group
        self.group.delete()

        # Post should also be deleted
        with self.assertRaises(GroupPost.DoesNotExist):
            GroupPost.objects.get(id=post_id)

    def test_group_post_empty_content(self):
        """Test that empty content is not allowed."""
        invalid_data = self.valid_post_data.copy()
        invalid_data['content'] = ''

        post = GroupPost(**invalid_data)
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_group_post_empty_user_id(self):
        """Test that empty user_id is not allowed."""
        invalid_data = self.valid_post_data.copy()
        invalid_data['user_id'] = ''

        post = GroupPost(**invalid_data)
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_group_post_foreign_key_relationship(self):
        """Test foreign key relationship with Group model."""
        post = GroupPost.objects.create(**self.valid_post_data)

        # Test forward relationship
        self.assertEqual(post.group, self.group)

        # Test reverse relationship
        self.assertIn(post, self.group.posts.all())

    def test_group_post_related_name(self):
        """Test reverse relationship using related_name 'posts'."""
        post = GroupPost.objects.create(**self.valid_post_data)

        # Access posts through the related_name
        group_posts = self.group.posts.all()
        self.assertIn(post, group_posts)

    def test_group_post_string_representation(self):
        """Test the __str__ method returns expected format."""
        post = GroupPost.objects.create(**self.valid_post_data)

        expected_str = f'user123 in Test Group for Posts: This is a test post!...'
        self.assertEqual(str(post), expected_str)

    def test_group_post_updated_at_changes(self):
        """Test that updated_at changes when post is modified."""
        post = GroupPost.objects.create(**self.valid_post_data)
        original_updated_at = post.updated_at

        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.001)

        # Update the post
        post.content = 'Modified content'
        post.save()

        self.assertGreater(post.updated_at, original_updated_at)


class GroupInviteModelTest(TestCase):
    def setUp(self):
        # Create a group without specifying ID to avoid conflicts
        self.group = Group.objects.create(
            name='Test Group for Invites',
            description='A test group for invites',
            creator_id='user123',
            creator_name='Test User',
            moderators=['user123'],
            moderator_names=['Test User'],
            members=['user123'],
            member_names=['Test User']
        )

        self.valid_invite_data = {
            'group': self.group,
            'inviter_id': 'user123',
            'invitee_id': 'user456'
        }

        # Create a second group for testing multiple invites
        self.second_group = Group.objects.create(
            name='Second Group for Invites',
            description='Another test group for invites',
            creator_id='user456',
            creator_name='User456',
            moderators=['user456'],
            moderator_names=['User456'],
            members=['user456'],
            member_names=['User456']
        )

    def test_create_valid_group_invite(self):
        """Test creating a valid group invite with all required fields."""
        invite = GroupInvite.objects.create(**self.valid_invite_data)
        self.assertEqual(invite.group, self.group)
        self.assertEqual(invite.invitee_id, 'user456')
        self.assertEqual(invite.inviter_id, 'user123')
        self.assertIsNotNone(invite.created_at)
        self.assertIsNotNone(invite.id)

    def test_group_invite_string_representation(self):
        """Test the __str__ method returns expected format."""
        invite = GroupInvite.objects.create(**self.valid_invite_data)
        expected_str = f"Invitee to {invite.group.name} for {invite.invitee_id}"
        self.assertEqual(str(invite), expected_str)

    def test_group_invite_foreign_key_relationship(self):
        """Test foreign key relationship with Group model."""
        invite = GroupInvite.objects.create(**self.valid_invite_data)
        self.assertEqual(invite.group.id, self.group.id)
        self.assertEqual(invite.group.name, 'Test Group for Invites')

    def test_group_invite_related_name(self):
        """Test reverse relationship using related_name 'invites'."""
        invite1 = GroupInvite.objects.create(**self.valid_invite_data)
        invite2_data = self.valid_invite_data.copy()
        invite2_data['invitee_id'] = 'user789'
        invite2 = GroupInvite.objects.create(**invite2_data)

        group_invites = self.group.invites.all()
        self.assertEqual(group_invites.count(), 2)
        self.assertIn(invite1, group_invites)
        self.assertIn(invite2, group_invites)

    def test_group_invite_cascade_delete(self):
        """Test that invites are deleted when group is deleted."""
        GroupInvite.objects.create(**self.valid_invite_data)
        invite2_data = self.valid_invite_data.copy()
        invite2_data['invitee_id'] = 'user789'
        GroupInvite.objects.create(**invite2_data)

        self.assertEqual(GroupInvite.objects.count(), 2)

        self.group.delete()
        self.assertEqual(GroupInvite.objects.count(), 0)

    def test_group_invite_empty_invitee_id(self):
        """Test that empty invitee_id is not allowed."""
        invite_data = self.valid_invite_data.copy()
        invite_data['invitee_id'] = ''

        invite = GroupInvite(**invite_data)
        with self.assertRaises(ValidationError):
            invite.full_clean()

    def test_group_invite_empty_inviter_id(self):
        """Test that empty inviter_id is not allowed."""
        invite_data = self.valid_invite_data.copy()
        invite_data['inviter_id'] = ''

        invite = GroupInvite(**invite_data)
        with self.assertRaises(ValidationError):
            invite.full_clean()

    def test_group_invite_auto_timestamp(self):
        """Test that created_at is automatically set."""
        invite = GroupInvite.objects.create(**self.valid_invite_data)
        self.assertIsNotNone(invite.created_at)

    def test_multiple_invites_same_group(self):
        """Test multiple invites can be created for the same group."""
        invite1 = GroupInvite.objects.create(**self.valid_invite_data)
        invite2_data = self.valid_invite_data.copy()
        invite2_data['invitee_id'] = 'user789'
        invite2 = GroupInvite.objects.create(**invite2_data)

        self.assertEqual(invite1.group, invite2.group)
        self.assertNotEqual(invite1.invitee_id, invite2.invitee_id)

    def test_same_user_multiple_invites(self):
        """Test same user can be invited to multiple groups."""
        group2 = Group.objects.create(
            name='Second Group for Multiple Invites',
            creator_id='user456',
            moderators=['user456'],
            moderator_names=['User456'],
            members=['user456'],
            member_names=['User456']
        )

        invite1 = GroupInvite.objects.create(**self.valid_invite_data)
        invite2_data = {
            'group': group2,
            'invitee_id': 'user456',  # Same invitee
            'inviter_id': 'user456'
        }
        invite2 = GroupInvite.objects.create(**invite2_data)

        self.assertEqual(invite1.invitee_id, invite2.invitee_id)
        self.assertNotEqual(invite1.group, invite2.group)