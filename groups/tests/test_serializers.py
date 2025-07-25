from django.test import TestCase
from rest_framework.test import APIRequestFactory
from ..models import Group, GroupPost, GroupInvite
from ..serializers import GroupSerializer, GroupPostSerializer, GroupInviteSerializer


class GroupSerializerTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.valid_group_data = {
            'name': 'Test Group',
            'description': 'A test group',
            'creator_id': 'user123',
            'admins': ['user123'],
            'members': ['user123']
        }
        self.valid_serializer_data = {
            'name': 'Test Group',
            'description': 'A test group'
        }

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        serializer = GroupSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], 'Test Group')
        self.assertEqual(serializer.validated_data['description'], 'A test group')

    def test_serializer_save_creates_group(self):
        """Test that serializer save creates a group object."""
        serializer = GroupSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())

        # Mock required fields (normally done in view)
        serializer.validated_data['creator_id'] = 'user123'
        serializer.validated_data['admins'] = ['user123']
        serializer.validated_data['members'] = ['user123']

        group = serializer.save()

        self.assertIsInstance(group, Group)
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.creator_id, 'user123')

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data_with_readonly = self.valid_serializer_data.copy()
        data_with_readonly.update({
            'id': 999,
            'creator_id': 'hacker123',
            'admins': ['hacker123'],
            'members': ['hacker123'],
            'created_at': '2023-01-01T00:00:00Z'
        })

        serializer = GroupSerializer(data=data_with_readonly)
        self.assertTrue(serializer.is_valid())

        # Check that read-only fields are not in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('creator_id', serializer.validated_data)
        self.assertNotIn('admins', serializer.validated_data)
        self.assertNotIn('members', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)

    def test_serializer_empty_name(self):
        """Test serializer with empty name."""
        data = {'name': '', 'description': 'Test description'}
        serializer = GroupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_serializer_missing_name(self):
        """Test serializer with missing name field."""
        data = {'description': 'Test description'}
        serializer = GroupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_serializer_name_too_long(self):
        """Test serializer with name exceeding 100 characters."""
        data = {'name': 'x' * 101, 'description': 'Test description'}
        serializer = GroupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_serializer_blank_description(self):
        """Test serializer with blank description (should be valid)."""
        data = {'name': 'Test Group', 'description': ''}
        serializer = GroupSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_missing_description(self):
        """Test serializer with missing description (should be valid)."""
        data = {'name': 'Test Group'}
        serializer = GroupSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_to_representation(self):
        """Test serializer converts model instance to dict representation."""
        group = Group.objects.create(**self.valid_group_data)
        serializer = GroupSerializer(group)

        expected_fields = ['id', 'name', 'description', 'creator_id', 'admins', 'members', 'created_at']
        for field in expected_fields:
            self.assertIn(field, serializer.data)

        self.assertEqual(serializer.data['name'], 'Test Group')
        self.assertEqual(serializer.data['creator_id'], 'user123')

    def test_serializer_many_groups(self):
        """Test serializer with many=True for multiple groups."""
        group1 = Group.objects.create(**self.valid_group_data)
        group2_data = self.valid_group_data.copy()
        group2_data['name'] = 'Second Group'
        group2 = Group.objects.create(**group2_data)

        groups = [group1, group2]
        serializer = GroupSerializer(groups, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['name'], 'Test Group')
        self.assertEqual(serializer.data[1]['name'], 'Second Group')

    def test_serializer_partial_update(self):
        """Test serializer with partial update (patch)."""
        group = Group.objects.create(**self.valid_group_data)
        update_data = {'description': 'Updated description'}

        serializer = GroupSerializer(group, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_group = serializer.save()
        self.assertEqual(updated_group.description, 'Updated description')
        self.assertEqual(updated_group.name, 'Test Group')  # Should remain unchanged


class GroupPostSerializerTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.group = Group.objects.create(
            name='Test Group',
            creator_id='user123',
            admins=['user123'],
            members=['user123']
        )
        self.valid_post_data = {
            'group': self.group,
            'user_id': 'user123',
            'content': 'This is a test post!'
        }
        self.valid_serializer_data = {
            'group': self.group.id,
            'content': 'This is a test post!'
        }

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        serializer = GroupPostSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['content'], 'This is a test post!')

    def test_serializer_save_creates_post(self):
        """Test that serializer save creates a group post object."""
        serializer = GroupPostSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())

        # Mock user_id assignment (normally done in view)
        serializer.validated_data['user_id'] = 'user123'
        post = serializer.save()

        self.assertIsInstance(post, GroupPost)
        self.assertEqual(post.content, 'This is a test post!')
        self.assertEqual(post.user_id, 'user123')
        self.assertEqual(post.group, self.group)

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data_with_readonly = self.valid_serializer_data.copy()
        data_with_readonly.update({
            'id': 999,
            'user_id': 'hacker123',
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-01-01T00:00:00Z'
        })

        serializer = GroupPostSerializer(data=data_with_readonly)
        self.assertTrue(serializer.is_valid())

        # Check that read-only fields are not in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('user_id', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)
        self.assertNotIn('updated_at', serializer.validated_data)

    def test_serializer_empty_content(self):
        """Test serializer with empty content."""
        data = {'group': self.group.id, 'content': ''}
        serializer = GroupPostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_missing_content(self):
        """Test serializer with missing content field."""
        data = {'group': self.group.id}
        serializer = GroupPostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_missing_group(self):
        """Test serializer with missing group field."""
        data = {'content': 'Test content'}
        serializer = GroupPostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('group', serializer.errors)

    def test_serializer_invalid_group_id(self):
        """Test serializer with invalid group ID."""
        data = {'group': 999, 'content': 'Test content'}
        serializer = GroupPostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('group', serializer.errors)

    def test_serializer_to_representation(self):
        """Test serializer converts model instance to dict representation."""
        post = GroupPost.objects.create(**self.valid_post_data)
        serializer = GroupPostSerializer(post)

        expected_fields = ['id', 'group', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, serializer.data)

        self.assertEqual(serializer.data['content'], 'This is a test post!')
        self.assertEqual(serializer.data['user_id'], 'user123')
        self.assertEqual(serializer.data['group'], self.group.id)

    def test_serializer_many_posts(self):
        """Test serializer with many=True for multiple posts."""
        post1 = GroupPost.objects.create(**self.valid_post_data)
        post2_data = self.valid_post_data.copy()
        post2_data['content'] = 'Second post'
        post2 = GroupPost.objects.create(**post2_data)

        posts = [post1, post2]
        serializer = GroupPostSerializer(posts, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['content'], 'This is a test post!')
        self.assertEqual(serializer.data[1]['content'], 'Second post')


class GroupInviteSerializerTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.group = Group.objects.create(
            name='Test Group',
            creator_id='user123',
            admins=['user123'],
            members=['user123']
        )
        self.valid_invite_data = {
            'group': self.group,
            'invitee_id': 'user456',
            'inviter_id': 'user123'
        }
        self.valid_serializer_data = {
            'group': self.group.id,
            'invitee_id': 'user456'
        }

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        serializer = GroupInviteSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['invitee_id'], 'user456')

    def test_serializer_save_creates_invite(self):
        """Test that serializer save creates a group invite object."""
        serializer = GroupInviteSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())

        # Mock inviter_id assignment (normally done in view)
        serializer.validated_data['inviter_id'] = 'user123'
        invite = serializer.save()

        self.assertIsInstance(invite, GroupInvite)
        self.assertEqual(invite.invitee_id, 'user456')
        self.assertEqual(invite.inviter_id, 'user123')
        self.assertEqual(invite.group, self.group)

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data_with_readonly = self.valid_serializer_data.copy()
        data_with_readonly.update({
            'id': 999,
            'inviter_id': 'hacker123',
            'created_at': '2023-01-01T00:00:00Z'
        })

        serializer = GroupInviteSerializer(data=data_with_readonly)
        self.assertTrue(serializer.is_valid())

        # Check that read-only fields are not in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('inviter_id', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)

    def test_serializer_empty_invitee_id(self):
        """Test serializer with empty invitee_id."""
        data = {'group': self.group.id, 'invitee_id': ''}
        serializer = GroupInviteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('invitee_id', serializer.errors)

    def test_serializer_missing_invitee_id(self):
        """Test serializer with missing invitee_id field."""
        data = {'group': self.group.id}
        serializer = GroupInviteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('invitee_id', serializer.errors)

    def test_serializer_missing_group(self):
        """Test serializer with missing group field."""
        data = {'invitee_id': 'user456'}
        serializer = GroupInviteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('group', serializer.errors)

    def test_serializer_invalid_group_id(self):
        """Test serializer with invalid group ID."""
        data = {'group': 999, 'invitee_id': 'user456'}
        serializer = GroupInviteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('group', serializer.errors)

    def test_serializer_to_representation(self):
        """Test serializer converts model instance to dict representation."""
        invite = GroupInvite.objects.create(**self.valid_invite_data)
        serializer = GroupInviteSerializer(invite)

        expected_fields = ['id', 'group', 'invitee_id', 'inviter_id', 'created_at']
        for field in expected_fields:
            self.assertIn(field, serializer.data)

        self.assertEqual(serializer.data['invitee_id'], 'user456')
        self.assertEqual(serializer.data['inviter_id'], 'user123')
        self.assertEqual(serializer.data['group'], self.group.id)

    def test_serializer_many_invites(self):
        """Test serializer with many=True for multiple invites."""
        invite1 = GroupInvite.objects.create(**self.valid_invite_data)
        invite2_data = self.valid_invite_data.copy()
        invite2_data['invitee_id'] = 'user789'
        invite2 = GroupInvite.objects.create(**invite2_data)

        invites = [invite1, invite2]
        serializer = GroupInviteSerializer(invites, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['invitee_id'], 'user456')
        self.assertEqual(serializer.data[1]['invitee_id'], 'user789')

    def test_serializer_long_invitee_id(self):
        """Test serializer with long invitee_id."""
        data = {'group': self.group.id, 'invitee_id': 'x' * 101}
        serializer = GroupInviteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('invitee_id', serializer.errors)