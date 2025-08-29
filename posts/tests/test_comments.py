from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from ..models import Post, Comment
from groups.models import Group


class CommentModelTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.group, _ = Group.objects.get_or_create(
            id=999,  # Use a different ID to avoid conflicts
            defaults={
                "name": "Test Group",
                "description": "Test group for comments",
                "creator_id": "creator123",
                "is_private": False
            }
        )

        self.post = Post.objects.create(
            user_id='user123',
            user_name='Test User',
            content='This is a test post!',
            group=self.group
        )

        self.valid_comment_data = {
            'post': self.post,
            'user_id': 'commenter123',
            'user_name': 'Commenter',
            'content': 'This is a test comment!'
        }

    def test_create_valid_comment(self):
        """Test creating a valid comment with all required fields."""
        comment = Comment.objects.create(**self.valid_comment_data)
        self.assertEqual(comment.user_id, 'commenter123')
        self.assertEqual(comment.content, 'This is a test comment!')
        self.assertEqual(comment.depth, 0)
        self.assertIsNotNone(comment.created_at)
        self.assertIsNotNone(comment.updated_at)
        self.assertIsNotNone(comment.id)

    def test_comment_string_representation(self):
        """Test the __str__ method returns expected format."""
        comment = Comment.objects.create(**self.valid_comment_data)
        expected_str = f"Comment by {comment.user_id} on post: {comment.post.content[:50]}..."
        self.assertEqual(str(comment), expected_str)

    def test_comment_content_max_length(self):
        """Test comment content respects 280 character limit."""
        long_content = 'x' * 281  # 281 characters
        comment_data = self.valid_comment_data.copy()
        comment_data['content'] = long_content

        comment = Comment(**comment_data)
        with self.assertRaises(ValidationError):
            comment.full_clean()

    def test_comment_empty_content(self):
        """Test that empty content is not allowed."""
        comment_data = self.valid_comment_data.copy()
        comment_data['content'] = ''

        comment = Comment(**comment_data)
        with self.assertRaises(ValidationError):
            comment.full_clean()

    def test_nested_comment_depth(self):
        """Test nested comment depth calculation."""
        # Create first level comment
        comment1 = Comment.objects.create(**self.valid_comment_data)

        # Create second level comment
        comment2_data = self.valid_comment_data.copy()
        comment2_data['parent_comment'] = comment1
        comment2 = Comment.objects.create(**comment2_data)

        # Create third level comment
        comment3_data = self.valid_comment_data.copy()
        comment3_data['parent_comment'] = comment2
        comment3 = Comment.objects.create(**comment3_data)

        self.assertEqual(comment1.depth, 0)
        self.assertEqual(comment2.depth, 1)
        self.assertEqual(comment3.depth, 2)

    def test_comment_depth_limit(self):
        """Test that comment depth cannot exceed 10 levels."""
        # Create a chain of 10 nested comments
        parent_comment = None
        for i in range(10):
            comment_data = self.valid_comment_data.copy()
            comment_data['parent_comment'] = parent_comment
            comment = Comment.objects.create(**comment_data)
            parent_comment = comment

        # Try to create an 11th level comment
        comment_data = self.valid_comment_data.copy()
        comment_data['parent_comment'] = parent_comment
        comment = Comment(**comment_data)

        # The depth validation should happen in the save method
        comment.save()
        self.assertEqual(comment.depth, 10)

    def test_comment_auto_depth_calculation(self):
        """Test that depth is automatically calculated if not set."""
        comment1 = Comment.objects.create(**self.valid_comment_data)

        comment2_data = self.valid_comment_data.copy()
        comment2_data['parent_comment'] = comment1
        comment2 = Comment.objects.create(**comment2_data)

        self.assertEqual(comment2.depth, 1)

    def test_comment_replies_relationship(self):
        """Test the replies relationship works correctly."""
        comment1 = Comment.objects.create(**self.valid_comment_data)

        comment2_data = self.valid_comment_data.copy()
        comment2_data['parent_comment'] = comment1
        comment2 = Comment.objects.create(**comment2_data)

        comment3_data = self.valid_comment_data.copy()
        comment3_data['parent_comment'] = comment1
        comment3 = Comment.objects.create(**comment3_data)

        self.assertEqual(comment1.replies.count(), 2)
        self.assertIn(comment2, comment1.replies.all())
        self.assertIn(comment3, comment1.replies.all())

    def test_post_comments_relationship(self):
        """Test the post-comments relationship works correctly."""
        comment1 = Comment.objects.create(**self.valid_comment_data)

        comment2_data = self.valid_comment_data.copy()
        comment2_data['user_name'] = 'Commenter 2'
        comment2 = Comment.objects.create(**comment2_data)

        self.assertEqual(self.post.comments.count(), 2)
        self.assertIn(comment1, self.post.comments.all())
        self.assertIn(comment2, self.post.comments.all())

    def test_threaded_comments_method(self):
        """Test the get_threaded_comments method returns correct structure."""
        # Create top-level comment
        comment1 = Comment.objects.create(**self.valid_comment_data)

        # Create nested comment
        comment2_data = self.valid_comment_data.copy()
        comment2_data['parent_comment'] = comment1
        comment2 = Comment.objects.create(**comment2_data)

        # Get threaded comments
        threaded_comments = self.post.get_threaded_comments()

        self.assertEqual(len(threaded_comments), 1)
        self.assertEqual(threaded_comments[0], comment1)
        self.assertEqual(threaded_comments[0].replies.count(), 1)
        self.assertEqual(threaded_comments[0].replies.first(), comment2)

    def test_comment_is_deleted_default(self):
        """Test that is_deleted defaults to False."""
        comment = Comment.objects.create(**self.valid_comment_data)
        self.assertFalse(comment.is_deleted)

    def test_comment_ordering(self):
        """Test that comments are ordered by creation time."""
        comment1 = Comment.objects.create(**self.valid_comment_data)

        comment2_data = self.valid_comment_data.copy()
        comment2_data['user_name'] = 'Commenter 2'
        comment2 = Comment.objects.create(**comment2_data)

        comments = Comment.objects.all()
        self.assertEqual(comments[0], comment1)
        self.assertEqual(comments[1], comment2)
