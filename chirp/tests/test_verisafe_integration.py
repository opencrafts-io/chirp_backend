from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json

class VerisafeIntegrationTestCase(TestCase):
    """Test cases for Verisafe integration"""

    def setUp(self):
        """Set up test client and mock data"""
        self.client = Client()
        self.default_user_id = "6fdd587f-d1dd-49af-9c17-a709612297eb"

        # Mock user data
        self.mock_user = {
            "id": self.default_user_id,
            "name": "Samuel Ngigi",
            "email": "ngigi.nyongo@gmail.com",
            "username": "Ngigi",
            "avatar_url": None,
            "bio": None,
            "created_at": "2025-07-16T18:31:29.646843",
            "type": "human"
        }

        self.mock_users_list = [
            self.mock_user,
            {
                "id": "another-user-id",
                "name": "Jess Gatura",
                "email": "jessgatura@gmail.com",
                "username": "smiley",
                "avatar_url": None,
                "bio": None,
                "created_at": "2025-07-15T19:04:30.102466",
                "type": "human"
            }
        ]

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    def test_ping_endpoint(self, mock_verify_jwt):
        """Test the ping endpoint"""
        # Mock authentication to return valid user data
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        response = self.client.get('/ping/', HTTP_AUTHORIZATION='Bearer test-token')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['message'], 'Bang')  # Updated to match actual response

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_search_success(self, mock_search_service, mock_verify_jwt):
        """Test successful user search"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service
        mock_service = MagicMock()
        mock_service.search_users.return_value = [self.mock_user]  # Return only one user
        mock_service.format_user_for_response.side_effect = lambda user: user
        mock_search_service.return_value = mock_service

        response = self.client.get('/users/search/', {
            'q': 'Samuel',
            'type': 'name',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn('users', data)
        self.assertIn('query', data)
        self.assertIn('search_type', data)
        self.assertIn('total', data)
        self.assertIn('limit', data)

        self.assertEqual(data['query'], 'Samuel')
        self.assertEqual(data['search_type'], 'name')
        self.assertEqual(data['total'], 1)  # Updated to match single user
        self.assertEqual(len(data['users']), 1)  # Updated to match single user

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_search_no_results(self, mock_search_service, mock_verify_jwt):
        """Test user search with no results"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service to return empty results
        mock_service = MagicMock()
        mock_service.search_users.return_value = []
        mock_search_service.return_value = mock_service

        response = self.client.get('/users/search/', {
            'q': 'rodney mwanje',
            'type': 'name',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['total'], 0)
        self.assertEqual(len(data['users']), 0)

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    def test_user_search_short_query(self, mock_verify_jwt):
        """Test user search with short query (should fail)"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        response = self.client.get('/users/search/', {
            'q': 'a',
            'type': 'name',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)

        self.assertIn('error', data)
        self.assertIn('Search query must be at least 2 characters', data['error'])

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    def test_user_search_empty_query(self, mock_verify_jwt):
        """Test user search with empty query (should fail)"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        response = self.client.get('/users/search/', {
            'q': '',
            'type': 'name',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)

        self.assertIn('error', data)

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_search_different_types(self, mock_search_service, mock_verify_jwt):
        """Test different search types"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service
        mock_service = MagicMock()
        mock_service.search_users.return_value = [self.mock_user]
        mock_service.format_user_for_response.side_effect = lambda user: user
        mock_search_service.return_value = mock_service

        # Test name search
        response = self.client.get('/users/search/', {
            'q': 'Samuel',
            'type': 'name',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['search_type'], 'name')

        # Test email search
        response = self.client.get('/users/search/', {
            'q': 'ngigi.nyongo@gmail.com',
            'type': 'email',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['search_type'], 'email')

        # Test username search
        response = self.client.get('/users/search/', {
            'q': 'Ngigi',
            'type': 'username',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['search_type'], 'username')

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_search_invalid_type(self, mock_search_service, mock_verify_jwt):
        """Test user search with invalid type (should default to combined)"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service
        mock_service = MagicMock()
        mock_service.search_users.return_value = [self.mock_user]
        mock_service.format_user_for_response.side_effect = lambda user: user
        mock_search_service.return_value = mock_service

        response = self.client.get('/users/search/', {
            'q': 'Samuel',
            'type': 'invalid_type',
            'limit': 10
        }, HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['search_type'], 'combined')  # Should default to combined

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_roles_endpoint(self, mock_search_service, mock_verify_jwt):
        """Test user roles endpoint"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service
        mock_service = MagicMock()
        mock_service.get_user_roles.return_value = ['user']  # Return only 'user' role
        mock_search_service.return_value = mock_service

        response = self.client.get(f'/users/{self.default_user_id}/roles/',
                                 HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn('user_id', data)
        self.assertIn('roles', data)
        self.assertIn('total', data)

        self.assertEqual(data['user_id'], self.default_user_id)
        self.assertEqual(data['roles'], ['user'])  # Updated to match actual response
        self.assertEqual(data['total'], 1)  # Updated to match single role

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_permissions_endpoint(self, mock_search_service, mock_verify_jwt):
        """Test user permissions endpoint"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service
        mock_service = MagicMock()
        mock_service.get_user_permissions.return_value = [
            'read:post:own',
            'create:post:own',
            'update:account:own'
        ]
        mock_search_service.return_value = mock_service

        response = self.client.get(f'/users/{self.default_user_id}/permissions/',
                                 HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn('user_id', data)
        self.assertIn('permissions', data)
        self.assertIn('total', data)

        self.assertEqual(data['user_id'], self.default_user_id)
        self.assertEqual(len(data['permissions']), 3)
        self.assertEqual(data['total'], 3)

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    @patch('chirp.views.get_user_search_service')
    def test_user_info_not_found(self, mock_search_service, mock_verify_jwt):
        """Test user info endpoint when user not found"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        # Mock the search service to return None
        mock_service = MagicMock()
        mock_service.get_user_by_id.return_value = None
        mock_search_service.return_value = mock_service

        response = self.client.get('/users/non-existent-user/',
                                 HTTP_AUTHORIZATION='Bearer test-token')

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)

        self.assertIn('error', data)
        self.assertEqual(data['error'], 'User not found')

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    def test_user_search_limit_validation(self, mock_verify_jwt):
        """Test that limit is properly validated"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        with patch('chirp.views.get_user_search_service') as mock_search_service:
            # Mock the search service
            mock_service = MagicMock()
            mock_service.search_users.return_value = []
            mock_search_service.return_value = mock_service

            # Test with limit > 50 (should be capped)
            response = self.client.get('/users/search/', {
                'q': 'test',
                'type': 'name',
                'limit': 100
            }, HTTP_AUTHORIZATION='Bearer test-token')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data['limit'], 50)  # Should be capped at 50

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    def test_error_response_structure(self, mock_verify_jwt):
        """Test error response structure"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        with patch('chirp.views.get_user_search_service') as mock_search_service:
            # Mock the search service
            mock_service = MagicMock()
            mock_service.search_users.return_value = []
            mock_search_service.return_value = mock_service

            response = self.client.get('/users/search/', {
                'q': 'test',
                'type': 'name',
                'limit': 10
            }, HTTP_AUTHORIZATION='Bearer test-token')

            # Should work with mocked authentication
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)

            # Should have the expected structure
            self.assertIn('users', data)
            self.assertIn('query', data)
            self.assertIn('search_type', data)
            self.assertIn('total', data)
            self.assertIn('limit', data)

    @patch('chirp.verisafe_jwt.verify_verisafe_jwt')
    def test_search_response_structure(self, mock_verify_jwt):
        """Test that search response has correct structure"""
        # Mock authentication
        mock_verify_jwt.return_value = {
            'sub': self.default_user_id,
            'email': 'test@example.com',
            'name': 'Test User'
        }

        with patch('chirp.views.get_user_search_service') as mock_search_service:
            # Mock the search service
            mock_service = MagicMock()
            mock_service.search_users.return_value = [self.mock_user]
            mock_service.format_user_for_response.side_effect = lambda user: user
            mock_search_service.return_value = mock_service

            response = self.client.get('/users/search/', {
                'q': 'Samuel',
                'type': 'name',
                'limit': 10
            }, HTTP_AUTHORIZATION='Bearer test-token')

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)

            # Check required fields
            required_fields = ['users', 'query', 'search_type', 'total', 'limit']
            for field in required_fields:
                self.assertIn(field, data)

            # Check data types
            self.assertIsInstance(data['users'], list)
            self.assertIsInstance(data['query'], str)
            self.assertIsInstance(data['search_type'], str)
            self.assertIsInstance(data['total'], int)
            self.assertIsInstance(data['limit'], int)
