from django.test import TestCase
from rest_framework.test import APIRequestFactory
from ..models import Post
from ..serializers import PostSerializer


class PostSerializerTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.valid_post_data = {
            'user_id': 'user123',
            'content': 'This is a test post!'
        }
        self.valid_serializer_data = {
            'content': 'This is a test post!'
        }

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        serializer = PostSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['content'], 'This is a test post!')

    def test_serializer_save_creates_post(self):
        """Test that serializer save creates a post object."""
        serializer = PostSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())

        # Mock user_id assignment (normally done in view)
        serializer.validated_data['user_id'] = 'user123'
        post = serializer.save()

        self.assertIsInstance(post, Post)
        self.assertEqual(post.content, 'This is a test post!')
        self.assertEqual(post.user_id, 'user123')

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data_with_readonly = self.valid_serializer_data.copy()
        data_with_readonly.update({
            'id': 999,
            'user_id': 'hacker123',
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-01-01T00:00:00Z'
        })

        serializer = PostSerializer(data=data_with_readonly)
        self.assertTrue(serializer.is_valid())

        # Check that read-only fields are not in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('user_id', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)
        self.assertNotIn('updated_at', serializer.validated_data)

    def test_serializer_empty_content(self):
        """Test serializer with empty content."""
        data = {"content": ""}
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_missing_content(self):
        """Test serializer with missing content field."""
        data = {}
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_content_too_long(self):
        """Test serializer with content exceeding 280 characters."""
        data = {'content': 'x' * 281}
        serializer = PostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_content_at_max_length(self):
        """Test serializer with content at exactly 280 characters."""
        data = {'content': 'x' * 280}
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_to_representation(self):
        """Test serializer converts model instance to dict representation."""
        post = Post.objects.create(**self.valid_post_data)
        serializer = PostSerializer(post)

        expected_fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, serializer.data)

        self.assertEqual(serializer.data['content'], 'This is a test post!')
        self.assertEqual(serializer.data['user_id'], 'user123')

    def test_serializer_many_posts(self):
        """Test serializer with many=True for multiple posts."""
        post1 = Post.objects.create(**self.valid_post_data)
        post2_data = self.valid_post_data.copy()
        post2_data['content'] = 'Second post'
        post2 = Post.objects.create(**post2_data)

        all_posts = [post1, post2]
        serializer = PostSerializer(all_posts, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['content'], 'This is a test post!')
        self.assertEqual(serializer.data[1]['content'], 'Second post')

    def test_serializer_partial_update(self):
        """Test serializer with partial update (patch)."""
        post = Post.objects.create(**self.valid_post_data)
        update_data = {'content': 'Updated content'}

        serializer = PostSerializer(post, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_post = serializer.save()
        self.assertEqual(updated_post.content, 'Updated content')
        self.assertEqual(updated_post.user_id, 'user123')  # Should remain unchanged

    def test_serializer_validation_with_whitespace(self):
        """Test serializer handles whitespace-only content."""
        data = {"content": "   "}
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_special_characters(self):
        """Test serializer handles special characters in content."""
        special_content = 'Hello! 🌟 This has émojis and spécial chars: @#$%^&*()'
        data = {'content': special_content}
        serializer = PostSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Mock user_id assignment
        serializer.validated_data['user_id'] = 'user123'
        post = serializer.save()
        self.assertEqual(post.content, special_content)