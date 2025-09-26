from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.fields import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
)

from posts.models import Post, PostView
from posts.serializers import PostSerializer, PostViewSerializer
from users.models import User


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


# Post viewers metrics
class RecordPostViewerView(CreateAPIView):
    """Records a post viewer"""

    serializer_class = PostViewSerializer

    def perform_create(self, serializer):
        post_id = self.kwargs.get("id")

        try:
            post = Post.objects.get(id=post_id)
            user_id = self.request.user_id  or None

            if user_id is None or user_id == "":
                raise ValidationError(
                    f"Failed to parse your information from request context"
                )
            user = User.objects.get(user_id=user_id)

            obj, created = PostView.objects.get_or_create(post=post, user=user)

            serializer.instance = obj
        except Post.DoesNotExist:
            raise ValidationError(f"Post with id {post_id} does not exist")
        except User.DoesNotExist:
            raise ValidationError(f"User with id {user_id} does not exist yet")
        except Exception as e:
            raise e
