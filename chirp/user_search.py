from typing import List, Dict, Optional
from chirp.verisafe_client import get_verisafe_client
from django.core.cache import cache

class UserSearchService:
    """Service for searching users through Verisafe"""

    def __init__(self):
        self.verisafe_client = get_verisafe_client()

    def search_users(self, query: str, limit: int = 10, search_type: str = 'combined', cache_ttl: int = 300) -> List[Dict]:
        """Search users with caching

        Args:
            query: Search query string
            limit: Maximum number of results (default: 10, max: 50)
            search_type: Type of search - 'name', 'email', 'username', or 'combined'
            cache_ttl: Cache TTL in seconds (default: 5 minutes)
        """
        # Normalize and validate inputs
        query = query.strip()
        limit = min(limit, 50)  # Cap at 50 for performance

        if not query or len(query) < 2:
            return []

        # Create cache key based on search parameters
        cache_key = f"user_search:{hash(query)}:{limit}:{search_type}"
        cached_results = cache.get(cache_key)

        if cached_results:
            return cached_results

        # Perform search based on type
        if search_type == 'name':
            results = self.verisafe_client.search_users_by_name(query, limit)
        elif search_type == 'email':
            results = self.verisafe_client.search_users_by_email(query, limit)
        elif search_type == 'username':
            results = self.verisafe_client.search_users_by_username(query, limit)
        else:  # combined search
            results = self.verisafe_client.search_users_combined(query, limit)

        # Cache results
        cache.set(cache_key, results, cache_ttl)

        return results

    def search_users_by_name(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by name"""
        return self.search_users(query, limit, 'name')

    def search_users_by_email(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by email"""
        return self.search_users(query, limit, 'email')

    def search_users_by_username(self, query: str, limit: int = 10) -> List[Dict]:
        """Search users by username"""
        return self.search_users(query, limit, 'username')

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID from Verisafe"""
        cache_key = f"user_info:{user_id}"
        cached_user = cache.get(cache_key)

        if cached_user:
            return cached_user

        user_info = self.verisafe_client.get_user_info(user_id)

        if user_info:
            # Cache for 1 hour
            cache.set(cache_key, user_info, 3600)

        return user_info

    def get_user_roles(self, user_id: str) -> List[str]:
        """Get user roles with caching"""
        cache_key = f"user_roles:{user_id}"
        cached_roles = cache.get(cache_key)

        if cached_roles:
            return cached_roles

        roles = self.verisafe_client.get_user_roles(user_id)

        # Cache for 30 minutes
        cache.set(cache_key, roles, 1800)

        return roles

    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions with caching"""
        cache_key = f"user_permissions:{user_id}"
        cached_permissions = cache.get(cache_key)

        if cached_permissions:
            return cached_permissions

        permissions = self.verisafe_client.get_user_permissions(user_id)

        # Cache for 30 minutes
        cache.set(cache_key, permissions, 1800)

        return permissions

    def format_user_for_response(self, user: Dict) -> Dict:
        """Format user data for API response"""
        return {
            'id': user.get('id'),
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'username': user.get('username'),
            'avatar_url': user.get('avatar_url'),
            'bio': user.get('bio'),
            'created_at': user.get('created_at'),
            'type': user.get('type', 'human')
        }

# Global service instance
_user_search_service = None

def get_user_search_service() -> UserSearchService:
    """Get global user search service instance"""
    global _user_search_service
    if _user_search_service is None:
        _user_search_service = UserSearchService()
    return _user_search_service
