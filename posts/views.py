from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
)

from posts.models import Post
from posts.serializers import PostSerializer


class PostCreateView(CreateAPIView):
    """Creates a post."""

    serializer_class = PostSerializer


class ListPostView(ListAPIView):
    """Lists all posts on the system"""

    serializer_class = PostSerializer
    queryset = Post.objects.all()


class RetrievePostByIDView(RetrieveAPIView):
    """Retrieves a post by its id"""

    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "id"


class RetrievePostByAuthorView(RetrieveAPIView):
    """Retrieves a post by its author's id"""

    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "author"


class RetrievePostByCommunityView(RetrieveAPIView):
    """Retrieves a post by its community group"""

    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "group"


class DestroyPostView(DestroyAPIView):
    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "id"


class PostSearchView(ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self) -> QuerySet[Post]:

        q = self.request.GET.get("q", "").strip()

        # If the query is too short, return an empty queryset
        if not q or len(q) < 2:
            return Post.objects.none()

        return Post._default_manager.filter(
            Q(content__icontains=q) | Q(title__icontains=q)
        ).order_by("title")
