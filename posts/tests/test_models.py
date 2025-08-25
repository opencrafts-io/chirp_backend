from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from ..models import Post, Attachment


class postsModelTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.valid_post_data = {
            'user_id': 'user123',
            'content': 'This is a test post!'
        }

    def test_create_valid_post(self):
        """Test creating a valid post with all required fields."""
        post = Post.objects.create(**self.valid_post_data)
        self.assertEqual(post.user_id, 'user123')
        self.assertEqual(post.content, 'This is a test post!')
        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)
        self.assertIsNotNone(post.id)

    def test_post_string_representation(self):
        """Test the __str__ method returns expected format."""
        post = Post.objects.create(**self.valid_post_data)
        expected_str = f"{post.user_id}: {post.content}..."
        self.assertEqual(str(post), expected_str)

    def test_post_content_max_length(self):
        """Test post content respects 280 character limit."""
        long_content = 'x' * 281  # 281 characters
        post_data = self.valid_post_data.copy()
        post_data['content'] = long_content

        post = Post(**post_data)
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_post_content_at_max_length(self):
        """Test post content works at exactly 280 characters."""
        max_content = 'x' * 280  # Exactly 280 characters
        post_data = self.valid_post_data.copy()
        post_data['content'] = max_content

        post = Post.objects.create(**post_data)
        self.assertEqual(len(post.content), 280)

    def test_post_user_id_max_length(self):
        """Test user_id respects 100 character limit."""
        long_user_id = 'x' * 101  # 101 characters
        post_data = self.valid_post_data.copy()
        post_data['user_id'] = long_user_id

        post = Post(**post_data)
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_post_empty_content(self):
        """Test that empty content is not allowed."""
        post_data = self.valid_post_data.copy()
        post_data['content'] = ''

        post = Post(**post_data)
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_post_empty_user_id(self):
        """Test that empty user_id is not allowed."""
        post_data = self.valid_post_data.copy()
        post_data['user_id'] = ''

        post = Post(**post_data)
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_post_auto_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        post = Post.objects.create(**self.valid_post_data)
        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)

    def test_post_updated_at_changes(self):
        """Test that updated_at changes when post is modified."""
        post = Post.objects.create(**self.valid_post_data)
        original_updated_at = post.updated_at

        post.content = 'Updated content'
        post.save()

        self.assertNotEqual(post.updated_at, original_updated_at)

    def test_multiple_posts_same_user(self):
        """Test that same user can create multiple posts."""
        post1 = Post.objects.create(**self.valid_post_data)
        post2_data = self.valid_post_data.copy()
        post2_data['content'] = 'Second post'
        post2 = Post.objects.create(**post2_data)

        self.assertEqual(post1.user_id, post2.user_id)
        self.assertNotEqual(post1.content, post2.content)
        self.assertNotEqual(post1.id, post2.id)

    def test_post_ordering(self):
        """Test default ordering (if any) of posts."""
        post1 = Post.objects.create(**self.valid_post_data)
        post2_data = self.valid_post_data.copy()
        post2_data['content'] = 'Second post'
        post2 = Post.objects.create(**post2_data)

        all_posts = Post.objects.all()
        self.assertEqual(all_posts.count(), 2)
        # Verify both posts are retrieved
        self.assertIn(post1, all_posts)
        self.assertIn(post2, all_posts)


class PostDeletionTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user_id = 'test_user_123'
        self.post = Post.objects.create(
            user_id=self.user_id,
            content='Test post with attachments'
        )

    def test_post_deletion_deletes_attachments(self):
        """Test that deleting a post also deletes all its attachments"""
        # Create some attachments for the post
        attachment1 = Attachment.objects.create(
            post=self.post,
            attachment_type='image',
            file='test_image1.jpg',
            file_size=1024,
            original_filename='test_image1.jpg'
        )
        attachment2 = Attachment.objects.create(
            post=self.post,
            attachment_type='file',
            file='test_file1.pdf',
            file_size=2048,
            original_filename='test_file1.pdf'
        )

        # Verify attachments exist
        self.assertEqual(self.post.attachments.count(), 2)
        self.assertEqual(Attachment.objects.count(), 2)

        # Delete the post
        self.post.delete()

        # Verify attachments are also deleted
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertEqual(Post.objects.count(), 0)

    def test_attachment_deletion_handles_missing_files(self):
        """Test that attachment deletion handles missing files gracefully"""
        # Create an attachment with a non-existent file
        attachment = Attachment.objects.create(
            post=self.post,
            attachment_type='image',
            file='non_existent_file.jpg',
            file_size=1024,
            original_filename='non_existent_file.jpg'
        )

        # This should not raise an exception
        try:
            attachment.delete()
        except Exception as e:
            self.fail(f"Attachment deletion should handle missing files gracefully: {e}")

        # Verify attachment is deleted from database
        self.assertEqual(Attachment.objects.count(), 0)