from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    QuerySet,
    RetrieveAPIView,
)
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from users.serializers import UserSerializer

from .models import User


class UserPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class CreateUserView(CreateAPIView):
    serializer_class = UserSerializer


class LocalUserSearchView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_queryset(self) -> QuerySet[User]:
        """
        Return users whose username, name, or email contains the request's "q" parameter, ordered by name.

        If the "q" parameter is missing or shorter than 2 characters, no users are returned.

        Returns:
            QuerySet[User]: QuerySet of matching User objects ordered by `name`; an empty QuerySet if the query is missing or shorter than 2 characters.
        """
        q = self.request.GET.get("q", "").strip()

        # If the query is too short, return an empty queryset
        if not q or len(q) < 2:
            return User.objects.none()

        return User._default_manager.filter(
            Q(username__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
        ).order_by("name")


class UserRetrieveByIDApiView(RetrieveAPIView):
    """Retrieves a user specified by ID"""

    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"
    serializer_class = UserSerializer
    queryset = User.objects.all()

class UserRetrieveByUsernameApiView(RetrieveAPIView):
    """Retrieves a user specified by username"""

    lookup_field = "username"
    lookup_url_kwarg = "username"
    serializer_class = UserSerializer
    queryset = User.objects.all()




class UserListView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_queryset(self) -> QuerySet[User]:
        """
        Return the queryset used by the view.

        Returns:
            QuerySet[User]: A queryset containing all User instances.
        """
        return User.objects.all()
