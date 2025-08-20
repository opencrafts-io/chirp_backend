import requests
import json
import time
import hashlib
import base64
import sys
from django.conf import settings
from django.core.cache import cache
from typing import Optional, Dict, List

class VerisafeClient:
    """Client for interacting with Verisafe authentication service"""

    def __init__(self):
        self.base_url = getattr(settings, 'VERISAFE_BASE_URL', 'https://qaverisafe.opencrafts.io')
        self.service_token = getattr(settings, 'VERISAFE_SERVICE_TOKEN', None)
        self.token_cache_key = 'verisafe_service_token'
        self.token_expiry_cache_key = 'verisafe_token_expiry'

    def _is_test_environment(self):
        """Check if we're running in a test environment"""
        return (
            'test' in sys.argv or
            'pytest' in sys.argv[0] or
            'manage.py' in sys.argv[0] and 'test' in sys.argv
        )

    def _safe_cache_get(self, key: str):
        """Safely get from cache, return None if Redis is unavailable"""
        try:
            return cache.get(key)
        except Exception:
            # Redis connection failed, return None
            return None

    def _safe_cache_set(self, key: str, value, timeout: int):
        """Safely set cache, ignore if Redis is unavailable"""
        try:
            cache.set(key, value, timeout)
        except Exception:
            # Redis connection failed, ignore
            pass

    def _get_service_token(self) -> Optional[str]:
        """Get cached service token or fetch new one"""
        cached_token = self._safe_cache_get(self.token_cache_key)
        token_expiry = self._safe_cache_get(self.token_expiry_cache_key)

        if cached_token and token_expiry and time.time() < token_expiry:
            return cached_token

        # Token expired or not cached, fetch new one
        return self._refresh_service_token()

    def _refresh_service_token(self) -> Optional[str]:
        """Refresh the service token"""
        try:
            # In production, you'd have a bot account created in Verisafe
            # and use its service token for authentication
            if self.service_token:
                # Cache the token for 23 hours (assuming 24-hour expiry)
                self._safe_cache_set(self.token_cache_key, self.service_token, 23 * 3600)
                self._safe_cache_set(self.token_expiry_cache_key, time.time() + (23 * 3600), 23 * 3600)
                return self.service_token
        except Exception as e:
            print(f"Failed to refresh service token: {e}")
        return None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Verisafe API requests"""
        token = self._get_service_token()
        if token:
            return {
                'X-API-Key': token,
                'Content-Type': 'application/json'
            }
        return {'Content-Type': 'application/json'}

    def validate_jwt_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token with Verisafe"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/validate",
                headers=self._get_headers(),
                json={'token': token}
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                return None
            else:
                print(f"Verisafe validation error: {response.status_code}")
                return None

        except Exception as e:
            print(f"Failed to validate JWT with Verisafe: {e}")
            return None

    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information from Verisafe by searching for the user ID"""
        try:
            # Search for the user by searching all fields
            # This is a workaround since there's no direct user lookup endpoint
            search_results = self.search_users_combined(user_id, limit=50)

            # Look for exact ID match
            for user in search_results:
                if user.get('id') == user_id:
                    return user

            return None

        except Exception as e:
            print(f"Failed to get user info from Verisafe: {e}")
            return None

    def get_user_roles(self, user_id: str) -> List[str]:
        """Get user roles from Verisafe"""
        try:
            response = requests.get(
                f"{self.base_url}/roles/user/{user_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [role['role_name'] for role in data]
            else:
                return []

        except Exception as e:
            print(f"Failed to get user roles from Verisafe: {e}")
            return []

    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions from Verisafe"""
        try:
            response = requests.get(
                f"{self.base_url}/permissions/user/{user_id}",
                headers=self._get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return [perm['permission'] for perm in data]
            else:
                return []

        except Exception as e:
            print(f"Failed to get user permissions from Verisafe: {e}")
            return []

    def search_users(self, query: str, limit: int = 10, search_type: str = 'name') -> List[Dict]:
        """Search users in Verisafe database

        Args:
            query: Search query string
            limit: Maximum number of results (default: 10, max: 100)
            search_type: Type of search - 'name', 'email', or 'username'
        """
        try:
            # Use the correct endpoint based on search type
            if search_type == 'email':
                endpoint = f"{self.base_url}/accounts/search/email"
            elif search_type == 'username':
                endpoint = f"{self.base_url}/accounts/search/username"
            else:  # default to name search
                endpoint = f"{self.base_url}/accounts/search/name"

            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                params={'q': query, 'limit': min(limit, 100), 'offset': 0}
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('accounts', [])
            else:
                print(f"Failed to search users: {response.status_code}")
                return []

        except Exception as e:
            print(f"Failed to search users in Verisafe: {e}")
            return []

    def search_users_by_name(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by name"""
        return self.search_users(query, limit, 'name')

    def search_users_by_email(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by email"""
        return self.search_users(query, limit, 'email')

    def search_users_by_username(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by username"""
        return self.search_users(query, limit, 'username')

    def search_users_combined(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users across all fields (name, email, username) and combine results"""
        try:
            all_results = []
            seen_ids = set()

            # Search by name
            name_results = self.search_users_by_name(query, limit)
            for user in name_results:
                if user.get('id') not in seen_ids:
                    all_results.append(user)
                    seen_ids.add(user.get('id'))

            # Search by email if we haven't reached the limit
            if len(all_results) < limit:
                email_results = self.search_users_by_email(query, limit - len(all_results))
                for user in email_results:
                    if user.get('id') not in seen_ids:
                        all_results.append(user)
                        seen_ids.add(user.get('id'))

            # Search by username if we haven't reached the limit
            if len(all_results) < limit:
                username_results = self.search_users_by_username(query, limit - len(all_results))
                for user in username_results:
                    if user.get('id') not in seen_ids:
                        all_results.append(user)
                        seen_ids.add(user.get('id'))

            return all_results[:limit]

        except Exception as e:
            print(f"Failed to perform combined user search: {e}")
            return []

# Global client instance
_verisafe_client = None

def get_verisafe_client() -> VerisafeClient:
    """Get global Verisafe client instance"""
    global _verisafe_client
    if _verisafe_client is None:
        _verisafe_client = VerisafeClient()
    return _verisafe_client
