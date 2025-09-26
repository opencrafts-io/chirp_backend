from rest_framework.generics import ListAPIView, QuerySet
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from users.serializers import UserSerializer

from .models import User


class UserPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class LocalUserSearchView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_queryset(self) -> QuerySet[User]:

        q = self.request.GET.get("q", "").strip()

        # If the query is too short, return an empty queryset
        if not q or len(q) < 2:
            return User.objects.none()

        return User._default_manager.filter(
            Q(username__icontains=q)
            | Q(name__icontains=q)
            | Q(email__icontains=q)
        ).order_by("name")


class UserListView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.all()

