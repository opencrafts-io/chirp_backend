from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import User


class LocalUserSearchView(APIView):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        try:
            limit = min(int(request.GET.get('limit', 10)), 50)
        except Exception:
            limit = 10

        if not q or len(q) < 2:
            return Response({
                'error': 'Query must be at least 2 characters',
                'users': [],
                'total': 0,
                'limit': limit,
            }, status=status.HTTP_400_BAD_REQUEST)

        qs = User._default_manager.filter(
            Q(username__icontains=q) |
            Q(full_name__icontains=q) |
            Q(user_name__icontains=q)
        ).order_by('user_name')[:limit]

        users = [{
            'id': u.user_id,
            'email': u.email,
            'name': u.full_name or u.user_name,
            'username': u.username,
            'avatar_url': u.avatar_url,
            'vibe_points': u.vibe_points or 0,
        } for u in qs]

        return Response({
            'users': users,
            'query': q,
            'total': len(users),
            'limit': limit,
        })


class UserListView(APIView):
    def get(self, request):
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)

        users_qs = User._default_manager.all().order_by('user_name')

        paginator = Paginator(users_qs, page_size)

        try:
            page_obj = paginator.get_page(page)
        except:
            return Response({'error': 'Invalid page number'}, status=400)

        users = [{
            'id': u.user_id,
            'email': u.email,
            'name': u.full_name or u.user_name,
            'username': u.username,
            'avatar_url': u.avatar_url,
            'vibe_points': u.vibe_points or 0,
            'created_at': u.created_at.isoformat(),
            'updated_at': u.updated_at.isoformat(),
        } for u in page_obj]

        return Response({
            'users': users,
            'pagination': {
                'page': page_obj.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
               }
           })

class UserCountView(APIView):
    """Get total count of users in the database"""

    def get(self, request):
        total_count = User._default_manager.count()
        return Response({
            'total_users': total_count,
            'message': f'Total users in database: {total_count}'
        })
