from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

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
