from django.contrib.admindocs.views import user_has_model_view_permission
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)
import random

from django.db.models import F, ExpressionWrapper, FloatField
from rest_framework.views import Response
from communities.models import Community, CommunityMembership
from posts.models import Attachment, Comment, Post, PostView, PostVotes
from posts.serializers import (
    AttachmentSerializer,
    CommentSerializer,
    PostSerializer,
    PostViewSerializer,
    PostVoteSerializer,
)
from users.models import User


class PostCreateView(CreateAPIView):
    """Creates a post."""

    serializer_class = PostSerializer

    def get_queryset(self):
        # Required by DRF's CreateAPIView
        return Post.objects.all()

    def perform_create(self, serializer):
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})

        community = serializer.validated_data.get("community")
        if not community:
            raise ValidationError({"error": "Community must be provided."})
        # Check membership
        membership = CommunityMembership.objects.filter(
            community=community, user=user, banned=False
        ).first()
        if not membership:
            raise ValidationError(
                {"error": "You must be a member of this community to post."}
            )

        # Save post
        serializer.save(author=user, community=community, created_at=timezone.now())


class PostAttachmentCreateView(CreateAPIView):
    serializer_class = AttachmentSerializer


class ListPostAttachmentsView(ListAPIView):
    serializer_class = AttachmentSerializer

    def get_queryset(self) -> QuerySet[Attachment]:
        post_id = self.kwargs.get("post_id")
        try:
            Post.objects.get(id=post_id)
            return Attachment.objects.filter(post=post_id)
        except Post.DoesNotExist:
            raise ValidationError({"error": f"Post with id {post_id} does not exist"})
        except Exception as e:
            raise ValidationError({"error": f"Coud not satisfy your request."})


class PostsFeedView(ListAPIView):
    """
    Returns recommended posts from communities where the user
    is an active (non-banned) member. If the user is not a member
    of any community, returns a set of random posts with the same criteria.

    Recommendation score is calculated as follows:

    score = (upvotes * 3) - (downvotes * 2) + (comment_count * 2) + (views_count * 0.5)

    1. Upvotes have the highest positive weight.
    2. Downvotes strongly penalize.
    3. Comment activity is weighted higher than views.
    4. Views provide a smaller positive nudge.
    """

    serializer_class = PostSerializer

    def get_queryset(self)-> QuerySet[Post]:
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})

        # Check if the user is part of any community
        user_communities = user.community_memberships.filter(banned=False)

        # Initialize the user community posts queryset
        user_community_posts = Post.objects.none()

        if user_communities.exists():
            # User is part of one or more communities, prioritize posts from these communities
            user_community_posts = (
                Post.objects.filter(
                    community__community_memberships__user=user,
                    community__community_memberships__banned=False,
                )
                .annotate(
                    recommendation_score=ExpressionWrapper(
                        (F("upvotes") * 3)
                        - (F("downvotes") * 2)
                        + (F("comment_count") * 2)
                        + (F("views_count") * 0.5),
                        output_field=FloatField(),
                    )
                )
                .select_related("author", "community")
                .distinct()
                .order_by("-recommendation_score", "-created_at")
            )

        # Fetch public community posts
        public_community_posts = (
            Post.objects.filter(community__is_private=False)  # Only public communities
            .annotate(
                recommendation_score=ExpressionWrapper(
                    (F("upvotes") * 3)
                    - (F("downvotes") * 2)
                    + (F("comment_count") * 2)
                    + (F("views_count") * 0.5),
                    output_field=FloatField(),
                )
            )
            .order_by("-recommendation_score", "-created_at")
            .all()
        )

        public_community_posts = public_community_posts[:5]  # Limit to 5 random posts

        # Combine both querysets using Q objects for conditions
        combined_queryset = user_community_posts | public_community_posts

        # Return the combined queryset, properly ordered
        return combined_queryset.order_by("-recommendation_score", "-created_at")


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


class PostListByCommunityView(ListAPIView):
    """Retrieves all posts for a specific community group"""

    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "community"
    lookup_url_kwarg = "community_id"

    def get_queryset(self):
        # Retrieves the posts for a specific community
        community_id = self.kwargs.get(self.lookup_url_kwarg)
        return Post.objects.filter(community_id=community_id)


class DestroyPostView(DestroyAPIView):
    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "id"

    def perform_destroy(self, instance):
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})
        if instance.author != user:
            raise PermissionDenied("You can only delete your own posts.")
        instance.delete()


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

    def perform_destroy(self, instance):
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})

        if instance.author != user:
            raise PermissionDenied("You can only delete your own comments.")
        instance.delete()
