from django.db import transaction
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework import status
from silk.profiling.profiler import silk_profile
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    ListCreateAPIView,
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)
from rest_framework.response import Response
from rest_framework import status
from communities.models import CommunityMembership
from interactions.models import Block
from interactions.utils import get_mutual_blocked_ids
from posts.models import Attachment, Comment, Post, PostView, PostVotes
from posts.serializers import (
    AttachmentSerializer,
    CommentSerializer,
    PostSerializer,
    PostViewSerializer,
    PostVoteSerializer,
)
from posts.tasks import (
    send_push_notification_to_community_members,
    send_push_notification_to_post_creator,
)
from users.models import User


def notify_on_post_creation(post_id):
    """
    Orchestrator to trigger all asynchronous notification tasks
    associated with a new post.
    """
    send_push_notification_to_post_creator.delay(post_id)
    send_push_notification_to_community_members.delay(post_id)


class PostCreateView(CreateAPIView):
    """Creates a post."""

    serializer_class = PostSerializer

    def get_queryset(self):
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

        with transaction.atomic():
            post = serializer.save(
                author=user, community=community, created_at=timezone.now()
            )

            transaction.on_commit(lambda: notify_on_post_creation(post.id))


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
    Provides a personalized 'Hot' feed for the authenticated user.

    The feed implements a blended discovery model:
    1. CONTENT SELECTION:
       - Subscribed: Posts from communities the user has joined.
       - Discovery: Posts from public communities to encourage exploration.
       - Exclusions: Automatically filters out content from blocked users
         and blocked communities.

    2. RANKING LOGIC (Gravity Decay):
       Uses the 'Hot' algorithm defined in PostQuerySet. Posts are ranked by
       engagement (upvotes, comments, views) penalized by the time elapsed
       since creation (Age). This ensures the feed stays fresh and prevents
       old viral posts from stagnating at the top.

    3. PERMISSIONS:
       Requires a valid 'user_id' in the request context. Validates that
       the user exists and is not banned from the communities being served
    """

    serializer_class = PostSerializer

    @silk_profile(name="Feed QuerySet Construction")
    def get_queryset(self):
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})

        blocked_user_ids = get_mutual_blocked_ids(user)
        blocked_comm_ids = Block.objects.filter(
            blocker=user, block_type="community"
        ).values_list("blocked_community_id", flat=True)

        user_communities = CommunityMembership.objects.filter(
            user=user, banned=False
        ).values_list("community_id", flat=True)

        content_filter = Q(community_id__in=user_communities) | Q(
            community__private=False
        )

        queryset = (
            Post.objects.exclude(author_id__in=blocked_user_ids)
            .exclude(community_id__in=blocked_comm_ids)
            .filter(content_filter)
            .select_related("author", "community")
            .prefetch_related(
                "comments",
                "attachments",
                "comments__author",
            )
            .distinct()
        )

        return queryset.hot()


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
        return Post.objects.filter(community_id=community_id).hot()


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class PostVoteView(ListCreateAPIView):
    """
    Upvote or downvote a post.
    If a vote exists, update it; otherwise, create a new vote.
    """

    lookup_field = "post_id"

    serializer_class = PostVoteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.validated_data["post"]
        user = serializer.validated_data["user"]
        value = serializer.validated_data["value"]

        if value not in [PostVotes.UPVOTE, PostVotes.DOWNVOTE]:
            raise ValidationError("Invalid vote value. Must be 1 or -1.")

        vote, created = PostVotes.objects.update_or_create(
            post=post,
            user=user,
            defaults={"value": value},
        )
        return Response(
            self.get_serializer(vote).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def get(self, request, *args, **kwargs):
        post_id = self.kwargs["post_id"]
        try:
            user_id = self.request.user_id or ""
            user = User.objects.get(user_id=user_id)
            vote = PostVotes.objects.get(post_id=post_id, user=user)
            return Response(
                data=self.serializer_class(vote).data,
                status=status.HTTP_200_OK,
            )
        except PostVotes.DoesNotExist:
            return Response(
                data={"message": "No vote exists"}, status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                data={"message": "Current user does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )


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

    # def get_queryset(self):
    #     post_id = self.kwargs["post_id"]
    #     return Comment.objects.filter(post_id=post_id, parent=None).prefetch_related(
    #         "replies", "author"
    #     )

    def get_queryset(self):
        # Existing user extraction
        user_id = getattr(self.request, "user_id", None)
        user = User.objects.get(user_id=user_id)

        # Get mutual blocked IDs
        blocked_user_ids = get_mutual_blocked_ids(user)

        post_id = self.kwargs["post_id"]

        # Exclude comments from anyone in the mutual block list
        return (
            Comment.objects.filter(post_id=post_id, parent=None)
            .exclude(author_id__in=blocked_user_ids)
            .prefetch_related("replies", "author")
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
