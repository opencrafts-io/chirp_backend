from django.contrib.admindocs.views import user_has_model_view_permission
from django.db.models import Q, QuerySet
from rest_framework.fields import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)

from posts.models import Comment, Post, PostView, PostVotes
from posts.serializers import (
    CommentSerializer,
    PostSerializer,
    PostViewSerializer,
    PostVoteSerializer,
)
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
            user_id = self.request.user_id or None

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


class PostVoteView(CreateAPIView):
    """
    Upvote or downvote a post.
    If a vote exists, update it; otherwise, create a new vote.
    """

    serializer_class = PostVoteSerializer

    def perform_create(self, serializer):
        post = serializer.validated_data["post"]
        user = serializer.validated_data["user"]
        value = serializer.validated_data["value"]

        if value not in [PostVotes.UPVOTE, PostVotes.DOWNVOTE]:
            raise ValidationError("Invalid vote value. Must be 1 or -1.")

        obj, created = PostVotes.objects.update_or_create(
            post=post,
            user=user,
            defaults={"value": value},
        )
        serializer.instance = obj


class PostVoteDeleteView(DestroyAPIView):
    """
    Redact a vote by deleting the user's vote for a post.
    """

    lookup_field = "post_id"

    def get_object(self):
        post_id = self.kwargs["post_id"]

        try:
            user_id = self.request.user_id or ""
            user = User.objects.get(user_id=user_id)
            return PostVotes.objects.get(post_id=post_id, user=user)
        except PostVotes.DoesNotExist:
            raise ValidationError("No vote exists to delete.")
        except User.DoesNotExist:
            raise ValidationError(f"User with id {user_id} does not exist!")


class CommentListCreateView(ListCreateAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        post_id = self.kwargs["post_id"]
        return Comment.objects.filter(post_id=post_id, parent=None).prefetch_related(
            "replies", "author"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["current_depth"] = 0  # start depth counting
        return context


class CommentRetrieveView(RetrieveAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()
    lookup_field = "id"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["current_depth"] = 0
        return context


class CommentDestroyView(DestroyAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()
    lookup_field = "id"
