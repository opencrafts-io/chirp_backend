import os
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import User
from dotenv import load_dotenv

load_dotenv()  # load .env at the top


class UserEndpointsAuthTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        """
        Initialize class-level JWT and authentication headers for tests.
        
        Calls the superclass setup, reads TEST_VERISAFE_JWT from the environment into cls.jwt_token, and sets cls.auth_headers to a dict containing the HTTP Authorization header with value "Bearer <token>" for use in authenticated requests.
        """
        super().setUpClass()
        cls.jwt_token = os.getenv("TEST_VERISAFE_JWT")
        cls.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {cls.jwt_token}"}

    def setUp(self):
        # Create a test user
        """
        Prepare test fixtures for UserEndpointsAuthTestCase.
        
        Creates a test User with username "john_doe" and resolves the API endpoint URLs used by the tests:
        - create_url -> "register-user"
        - search_url -> "local_user_search"
        - list_url   -> "user_list"
        
        These attributes are stored on the test instance for use by test methods.
        """
        self.user = User.objects.create(
            username="john_doe",
            name="John Doe",
            email="john@example.com",
        )

        # API endpoints
        self.create_url = reverse("register-user")
        self.search_url = reverse("local_user_search")
        self.list_url = reverse("user_list")
    #
        def test_user_list_authenticated(self):
            """
            Verify that an authenticated request can retrieve the user list.
            
            Asserts that a GET to the user list endpoint with authentication returns HTTP 200 and that the response's "results" list contains at least one item.
            """
            response = self.client.get(self.list_url, **self.auth_headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertGreaterEqual(len(response.data["results"]), 1)

        def test_local_user_search_authenticated(self):
            response = self.client.get(self.search_url, {"q": "john"}, **self.auth_headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["results"][0]["username"], "john_doe")

        def test_create_user_authenticated(self):
            payload = {
                "username": "alice",
                "name": "Alice Wonderland",
                "email": "alice@example.com",
            }
            response = self.client.post(
                self.create_url, payload, format="json", **self.auth_headers
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(User.objects.filter(username="alice").exists())
