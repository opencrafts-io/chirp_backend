from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from chirp.user_search import get_user_search_service
from rest_framework.permissions import IsAdminUser
from django.conf import settings
from utils.sync_users import sync_users
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class PingView(APIView):
    """Health check endpoint"""
    def get(self, request):
        return Response({"message": "Bang"})

class UserSearchView(APIView):
    def get(self, request):
        """Search users through Verisafe"""
        query = request.GET.get('q', '').strip()
        limit = min(int(request.GET.get('limit', 10)), 50)  # Max 50 results
        search_type = request.GET.get('type', 'combined')  # name, email, username, combined

        if not query or len(query) < 2:
            return Response({
                'error': 'Search query must be at least 2 characters',
                'query': query,
                'users': [],
                'total': 0
            }, status=400)

        # Validate search type
        valid_types = ['name', 'email', 'username', 'combined']
        if search_type not in valid_types:
            search_type = 'combined'

        search_service = get_user_search_service()
        users = search_service.search_users(query, limit, search_type)

        # Format users for response
        formatted_users = [search_service.format_user_for_response(user) for user in users]

        return Response({
            'users': formatted_users,
            'query': query,
            'search_type': search_type,
            'total': len(formatted_users),
            'limit': limit
        })

class UserInfoView(APIView):
    def get(self, request, user_id):
        """Get user information from Verisafe"""
        search_service = get_user_search_service()
        user_info = search_service.get_user_by_id(user_id)

        if user_info:
            formatted_user = search_service.format_user_for_response(user_info)
            return Response(formatted_user)
        else:
            return Response({'error': 'User not found'}, status=404)

class UserRolesView(APIView):
    def get(self, request, user_id):
        """Get user roles from Verisafe"""
        search_service = get_user_search_service()
        roles = search_service.get_user_roles(user_id)

        return Response({
            'user_id': user_id,
            'roles': roles,
            'total': len(roles)
        })

class UserPermissionsView(APIView):
    def get(self, request, user_id):
        """Get user permissions from Verisafe"""
        search_service = get_user_search_service()
        permissions = search_service.get_user_permissions(user_id)

        return Response({
            'user_id': user_id,
            'permissions': permissions,
            'total': len(permissions)
        })


@method_decorator(csrf_exempt, name='dispatch')
class AdminMaintenanceView(APIView):
    """Admin-only endpoint to trigger user sync and backfill on server.

    Protect with a shared secret token in settings: MAINTENANCE_TOKEN
    """

    def post(self, request):
        action = request.data.get('action') or request.GET.get('action')
        limit = request.data.get('limit') or request.GET.get('limit')
        try:
            limit = int(limit) if limit is not None else 50
        except Exception:
            limit = 50

        if action == 'sync_users':
            total = sync_users(clear_first=False, limit=limit)
            return Response({'status': 'ok', 'synced': total})
        elif action == 'backfill':
            from utils.management.commands.backfill_user_denorm import Command as BackfillCommand
            cmd = BackfillCommand()
            cmd.handle(dry_run=False)
            return Response({'status': 'ok', 'backfill': True})
        else:
            return Response({'error': 'Unknown action'}, status=400)

    def get(self, request):
        return self.post(request)