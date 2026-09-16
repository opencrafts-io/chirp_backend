from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import Max, Q, QuerySet
from django.utils import timezone
from rest_framework import status
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
from rest_framework.views import APIView
from communities.models import CommunityMembership
from interactions.models import Block
from interactions.utils import get_mutual_blocked_ids
from posts.models import (
    Attachment,
    Comment,
    Poll,
    PollVote,
    Post,
    PostView,
    PostVotes,
)
from posts.serializers import (
    AttachmentSerializer,
    CommentSerializer,
    PollSerializer,
    PollVoteRequestSerializer,
    PollVoterSerializer,
    PostSerializer,
    PostViewSerializer,
    PostVoteSerializer,
)
from posts.tasks import (
    send_push_notification_to_community_members,
    send_push_notification_to_parent_comment_author_on_reply,
    send_push_notification_to_post_author_on_comment,
    send_push_notification_to_post_creator,
)
from users.models import User


def get_request_user(request) -> User:
    """
    Resolve the acting `User` from the `user_id` the auth layer attached to
    the request, raising the same ValidationErrors the other views use.
    """
    user_id = getattr(request, "user_id", None)
    if not user_id:
        raise ValidationError(
            {"error": "Failed to parse your information from request context"}
        )
    try:
        return User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        raise ValidationError({"error": f"User with id {user_id} does not exist"})


def ensure_poll_access(poll: Poll, user: User) -> None:
    """
    Mirror feed visibility for poll mutations/reads: private communities
    require a non-banned membership, banned members are refused everywhere,
    and mutual user blocks with the post author hide the poll entirely.
    """
    post = poll.post
    membership = CommunityMembership.objects.filter(
        community_id=post.community_id, user=user
    ).first()
    if membership is not None and membership.banned:
        raise PermissionDenied("You are banned from this community.")
    if post.community.private and membership is None:
        raise PermissionDenied("This poll belongs to a private community.")
    if post.author_id in get_mutual_blocked_ids(user):
        raise PermissionDenied("This poll is not available.")


def notify_on_post_creation(post_id):
    """
    Orchestrator to trigger all asynchronous notification tasks
    associated with a new post.
    """
    send_push_notification_to_post_creator.delay(post_id)
    send_push_notification_to_community_members.delay(post_id)


def notify_on_comment_creation(comment_id):
    """
    Orchestrator to trigger all asynchronous notification tasks
    associated with a new comment.
    """
    send_push_notification_to_post_author_on_comment.delay(comment_id)
    send_push_notification_to_parent_comment_author_on_reply.delay(comment_id)


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
            .with_polls(user_id)
            .distinct()
        )

        return queryset.hot()


class ListPostView(ListAPIView):
    """Lists all posts on the system"""

    serializer_class = PostSerializer

    def get_queryset(self):
        return Post.objects.with_polls(getattr(self.request, "user_id", None))


class RetrievePostByIDView(RetrieveAPIView):
    """Retrieves a post by its id"""

    serializer_class = PostSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Post.objects.with_polls(getattr(self.request, "user_id", None))


class RetrievePostByAuthorView(RetrieveAPIView):
    """Retrieves a post by its author's id"""

    serializer_class = PostSerializer
    lookup_field = "author"

    def get_queryset(self):
        return Post.objects.with_polls(getattr(self.request, "user_id", None))


class PostListByCommunityView(ListAPIView):
    """Retrieves all posts for a specific community group"""

    serializer_class = PostSerializer
    queryset = Post.objects.all()
    lookup_field = "community"
    lookup_url_kwarg = "community_id"

    def get_queryset(self):
        # Retrieves the posts for a specific community
        community_id = self.kwargs.get(self.lookup_url_kwarg)
        return (
            Post.objects.filter(community_id=community_id)
            .with_polls(getattr(self.request, "user_id", None))
            .hot()
        )


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

        return (
            Post.objects.filter(Q(content__icontains=q) | Q(title__icontains=q))
            .with_polls(getattr(self.request, "user_id", None))
            .order_by("title")
        )


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

    def perform_create(self, serializer):
        with transaction.atomic():
            comment = serializer.save()
            transaction.on_commit(lambda: notify_on_comment_creation(comment.id))


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


# Polls
class PollVoteView(APIView):
    """
    POST   replaces the caller's selection on a poll with `option_ids`.
    DELETE removes the caller's selection entirely (idempotent).

    Both return the full, up-to-date poll (server-authoritative counts and
    the caller's `my_votes`) so the client can reconcile optimistic state.
    """

    def _locked_poll(self, poll_id: int, user: User) -> Poll:
        """Lock just the poll row (not the joined post) and check access."""
        try:
            poll = (
                Poll.objects.select_for_update(of=("self",))
                .select_related("post__community")
                .get(id=poll_id)
            )
        except Poll.DoesNotExist:
            raise ValidationError({"error": f"Poll with id {poll_id} does not exist"})
        ensure_poll_access(poll, user)
        return poll

    def _serialize(self, poll: Poll) -> Response:
        # Re-fetch options so the response carries the recounted totals.
        poll = Poll.objects.prefetch_related("options").get(id=poll.id)
        return Response(
            PollSerializer(poll, context={"request": self.request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, poll_id: int, *args, **kwargs):
        user = get_request_user(request)
        body = PollVoteRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        option_ids = list(dict.fromkeys(body.validated_data["option_ids"]))

        with transaction.atomic():
            poll = self._locked_poll(poll_id, user)

            if poll.is_closed:
                raise ValidationError({"error": "This poll has closed."})
            if not poll.allows_multiple and len(option_ids) > 1:
                raise ValidationError(
                    {"error": "This poll only allows a single choice."}
                )
            valid_ids = set(poll.options.values_list("id", flat=True))
            unknown = [oid for oid in option_ids if oid not in valid_ids]
            if unknown:
                raise ValidationError(
                    {"error": f"Options {unknown} do not belong to this poll."}
                )

            PollVote.objects.filter(poll=poll, user=user).delete()
            PollVote.objects.bulk_create(
                [PollVote(poll=poll, option_id=oid, user=user) for oid in option_ids]
            )
            poll.recount()

        return self._serialize(poll)

    def delete(self, request, poll_id: int, *args, **kwargs):
        user = get_request_user(request)

        with transaction.atomic():
            poll = self._locked_poll(poll_id, user)
            # Final results must stay final: no retractions after close.
            if poll.is_closed:
                raise ValidationError({"error": "This poll has closed."})
            PollVote.objects.filter(poll=poll, user=user).delete()
            poll.recount()

        return self._serialize(poll)


class PollVotersListView(ListAPIView):
    """
    Paginated list of who voted on a poll, one row per voter with every
    option they picked. Optional `option_id` narrows to voters of that
    option. On anonymous polls only the post author may call this.
    """

    serializer_class = PollVoterSerializer

    def get_poll(self) -> Poll:
        try:
            return Poll.objects.select_related("post__community").get(
                id=self.kwargs["poll_id"]
            )
        except Poll.DoesNotExist:
            raise ValidationError(
                {"error": f"Poll with id {self.kwargs['poll_id']} does not exist"}
            )

    def get_queryset(self):
        user = get_request_user(self.request)
        poll = self.get_poll()
        ensure_poll_access(poll, user)

        if poll.is_anonymous and poll.post.author_id != user.user_id:
            raise PermissionDenied("Votes on this poll are anonymous.")

        votes = PollVote.objects.filter(poll=poll)

        option_id = self.request.query_params.get("option_id")
        if option_id:
            try:
                option_id = int(option_id)
            except ValueError:
                raise ValidationError({"error": "option_id must be an integer."})
            voter_ids = votes.filter(option_id=option_id).values("user_id")
            votes = votes.filter(user_id__in=voter_ids)

        # One row per voter: aggregate their option ids and latest vote time.
        return (
            votes.values("user_id")
            .annotate(
                option_ids=ArrayAgg("option_id", order_by="option__position"),
                voted_at=Max("created_at"),
            )
            .order_by("-voted_at", "user_id")
        )

    @staticmethod
    def _attach_users(rows):
        """Attach User objects in one query for the nested `user` field."""
        users = User.objects.in_bulk([row["user_id"] for row in rows])
        for row in rows:
            row["user"] = users.get(row["user_id"])
        return rows

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        rows = self._attach_users(page if page is not None else list(queryset))
        serializer = self.get_serializer(rows, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
