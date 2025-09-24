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
        start_page = request.data.get('start_page') or request.GET.get('start_page')
        max_pages = request.data.get('max_pages') or request.GET.get('max_pages')

        try:
            limit = int(limit) if limit is not None else 50
        except Exception:
            limit = 50

        try:
            start_page = int(start_page) if start_page is not None else 1
        except Exception:
            start_page = 1

        try:
            max_pages = int(max_pages) if max_pages is not None else None
        except Exception:
            max_pages = None

        if action == 'sync_users':
            try:
                total = sync_users(clear_first=False, limit=limit, start_page=start_page, max_pages=max_pages)
                return Response({
                    'status': 'ok',
                    'synced': total,
                    'start_page': start_page,
                    'max_pages': max_pages,
                    'next_page': start_page + (max_pages or 1)
                })
            except Exception as e:
                return Response({'status': 'error', 'message': str(e)}, status=500)
        elif action == 'backfill':
            try:
                from utils.management.commands.backfill_user_denorm import Command as BackfillCommand
                cmd = BackfillCommand()
                cmd.handle(dry_run=False)
                return Response({'status': 'ok', 'backfill': True})
            except Exception as e:
                return Response({'status': 'error', 'message': str(e)}, status=500)
        elif action == 'backfill_userrefs':
            try:
                from posts.models import Post
                from users.models import User
                updated = 0
                missing_user = 0
                qs = Post._default_manager.all().select_related('user_ref')
                for p in qs:
                    if p.user_ref:
                        u = p.user_ref
                    else:
                        u = User._default_manager.filter(user_id=p.user_id).only('user_name', 'email').first()
                        if not u:
                            missing_user += 1
                            continue
                    changed_fields = []
                    if p.user_ref_id != u.pk:
                        p.user_ref = u
                        changed_fields.append('user_ref')
                    if p.user_name != u.user_name:
                        p.user_name = u.user_name
                        changed_fields.append('user_name')
                    if (p.email or '') != (u.email or ''):
                        p.email = u.email
                        changed_fields.append('email')
                    if changed_fields:
                        p.save(update_fields=list(set(changed_fields)))
                        updated += 1
                return Response({'status': 'ok', 'updated_posts': updated, 'missing_user_refs': missing_user})
            except Exception as e:
                return Response({'status': 'error', 'message': str(e)}, status=500)
        else:
            return Response({'error': 'Unknown action'}, status=400)

    def get(self, request):
        return self.post(request)