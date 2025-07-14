from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import Mock, patch
from ..models import Post
from ..views import PostListCreateView
from ..serializers import StatusSerializer


class postsListCreateViewTest(TestCase):

    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.view = PostListCreateView.as_view()
        self.valid_post_data = {
            'user_id': 'user123',
            'content': 'This is a test post!'
        }
        self.valid_request_data = {
            'content': 'This is a test post!'
        }

    def test_get_empty_queryset(self):
        """Test GET request with no posts in database."""
        request = self.factory.get('/statuses/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_with_posts(self):
        """Test GET request returns all posts."""
        # Create test posts
        post1 = Post.objects.create(**self.valid_post_data)
        post2_data = self.valid_post_data.copy()
        post2_data['content'] = 'Second post'
        post2_data['user_id'] = 'user456'
        post2 = Post.objects.create(**post2_data)

        request = self.factory.get('/statuses/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn('content', response.data[0])
        self.assertIn('user_id', response.data[0])
        self.assertIn('created_at', response.data[0])

    def test_get_posts_serialization(self):
        """Test that GET request properly serializes posts."""
        post = Post.objects.create(**self.valid_post_data)

        request = self.factory.get('/statuses/')
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['content'], 'This is a test post!')
        self.assertEqual(response.data[0]['user_id'], 'user123')
        self.assertEqual(response.data[0]['id'], post.id)

    def test_post_valid_data(self):
        """Test POST request with valid data creates post."""
        request = self.factory.post('/statuses/', self.valid_request_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)

        created_post = Post.objects.first()
        self.assertEqual(created_post.content, 'This is a test post!')
        self.assertEqual(created_post.user_id, 'user123')

    def test_post_assigns_user_id_from_request(self):
        """Test POST request assigns user_id from request object."""
        request = self.factory.post('/statuses/', self.valid_request_data)
        request.user_id = 'authenticated_user'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_id'], 'authenticated_user')

    def test_post_invalid_data(self):
        """Test POST request with invalid data returns 400."""
        invalid_data = {'content': ''}  # Empty content
        request = self.factory.post('/statuses/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertEqual(Post.objects.count(), 0)

    def test_post_missing_content(self):
        """Test POST request with missing content field."""
        invalid_data = {}
        request = self.factory.post('/statuses/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_post_content_too_long(self):
        """Test POST request with content exceeding 280 characters."""
        invalid_data = {'content': 'x' * 281}
        request = self.factory.post('/statuses/', invalid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_post_content_at_max_length(self):
        """Test POST request with content at exactly 280 characters."""
        valid_data = {'content': 'x' * 280}
        request = self.factory.post('/statuses/', valid_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['content']), 280)

    def test_post_response_format(self):
        """Test POST request returns proper response format."""
        request = self.factory.post('/statuses/', self.valid_request_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_post_data_copy_modification(self):
        """Test that POST request modifies copy of data, not original."""
        original_data = self.valid_request_data.copy()
        request = self.factory.post('/statuses/', original_data)
        request.user_id = 'user123'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Original data should not have user_id
        self.assertNotIn('user_id', original_data)

    def test_post_multiple_posts_same_user(self):
        """Test user can create multiple posts."""
        request1 = self.factory.post('/statuses/', self.valid_request_data)
        request1.user_id = 'user123'

        request2_data = {'content': 'Second post'}
        request2 = self.factory.post('/statuses/', request2_data)
        request2.user_id = 'user123'

        response1 = self.view(request1)
        response2 = self.view(request2)

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 2)

    def test_view_uses_correct_serializer(self):
        """Test that view uses StatusSerializer."""
        request = self.factory.get('/statuses/')
        request.user_id = 'user123'

        with patch('posts.views.StatusSerializer') as mock_serializer:
            mock_serializer.return_value.data = []
            response = self.view(request)
            mock_serializer.assert_called()

    def test_get_queryset_all_posts(self):
        """Test GET request retrieves all posts (no filtering by user)."""

        post1 = Post.objects.create(user_id='user1', content='post 1')
        post2 = Post.objects.create(user_id='user2', content='post 2')

        request = self.factory.get('/statuses/')
        request.user_id = 'user3'

        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)