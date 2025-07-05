from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
import json


class PingEndpointTest(TestCase):
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.ping_url = '/ping/'

    def test_ping_endpoint_returns_bang(self):
        """Test that ping endpoint returns 'Bang' message."""
        response = self.client.get(self.ping_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')

        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Bang')

    def test_ping_endpoint_with_reverse_url(self):
        """Test ping endpoint using reverse URL lookup."""
        response = self.client.get(reverse('ping'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Bang')

    def test_ping_endpoint_only_allows_get(self):
        """Test that ping endpoint only allows GET requests."""
        # Test POST request returns 405 Method Not Allowed
        response = self.client.post(self.ping_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test PUT request returns 405 Method Not Allowed
        response = self.client.put(self.ping_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE request returns 405 Method Not Allowed
        response = self.client.delete(self.ping_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_ping_endpoint_no_authentication_required(self):
        """Test that ping endpoint doesn't require authentication."""
        # Should work without any authentication headers
        response = self.client.get(self.ping_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = json.loads(response.content)
        self.assertEqual(response_data['message'], 'Bang')

    def test_ping_endpoint_response_format(self):
        """Test that ping endpoint returns proper JSON format."""
        response = self.client.get(self.ping_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that response is valid JSON
        response_data = json.loads(response.content)
        self.assertIsInstance(response_data, dict)
        self.assertIn('message', response_data)
        self.assertEqual(len(response_data), 1)  # Only one key