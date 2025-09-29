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

from django.db.models import F, ExpressionWrapper, FloatField
from communities.models import Community, CommunityMembership
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

    def get_queryset(self):
        # Required by DRF's CreateAPIView
        """
        Provide the base queryset for this view consisting of all Post records.
        
        Returns:
            QuerySet: All Post objects.
        """
        return Post.objects.all()

    def perform_create(self, serializer):
        """
        Create and save a new Post tied to the requesting user and specified community.
        
        Validates the requesting user's presence in the request context, ensures the user and community exist, verifies the user is a non-banned member of the community, and then saves the serializer with author, community, and created_at set.
        
        Parameters:
            serializer: DRF serializer instance containing validated post data to be saved.
        
        Raises:
            ValidationError: If the request's user_id is missing, the user does not exist, the community does not exist, or the user is not an active (non-banned) member of the community.
        """
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})

        community_id = self.kwargs.get("community_id")
        try:
            community = Community.objects.get(id=community_id)
        except Community.DoesNotExist:
            raise ValidationError({"error": "Community does not exist"})

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


class PostsFeedView(ListAPIView):
    """
    Returns recommended posts from communities where the user
    is an active (non-banned) member.
    Recommendations consider upvotes, downvotes, comments, and views.


    score = (upvotes * 3) - (downvotes * 2) + (comment_count * 2) + (views_count * 0.5)

    1. Upvotes have the highest positive weight.
    2. Downvotes strongly penalize.
    3. Comment activity is weighted higher than views.
    4. Views provide a smaller positive nudge
    """

    serializer_class = PostSerializer

    def get_queryset(self) -> QuerySet[Post]:
        """
        Return posts from communities where the requesting user is an active (not banned) member, ordered by recommendation score and creation time.
        
        Each returned Post is annotated with `recommendation_score`, has `author` and `community` selected, and the queryset is distinct.
        
        Returns:
            QuerySet[Post]: QuerySet of Post objects filtered and annotated for the requesting user.
        
        Raises:
            ValidationError: If the request lacks a `user_id` in its context or if no User exists with the provided `user_id`.
        """
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"error": f"User with id {user_id} does not exist"})

        return (
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

    def perform_destroy(self, instance):
        """
        Delete the given post instance if the requesting user (from request.user_id) is the post's author.
        
        Parameters:
            instance (Post): The Post model instance to delete.
        
        Raises:
            ValidationError: If the request is missing user information or the user does not exist.
            PermissionDenied: If the requesting user is not the author of the post.
        """
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

        """
        Return posts whose title or content contains the request's "q" parameter; if the query is absent or shorter than 2 characters, return an empty queryset.
        
        The search is case-insensitive and matches substrings in either `title` or `content`. Results are ordered by `title`.
        
        Returns:
            QuerySet[Post]: Posts matching the query, or an empty queryset when the query is missing or shorter than 2 characters.
        """
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
        """
        Create or retrieve a PostView for the specified post and request user, and attach it to the serializer instance.
        
        Validates that the post (from URL kwarg "id") and the request user exist; raises ValidationError if the post id is missing/invalid or the user id cannot be parsed or does not exist. On success, sets `serializer.instance` to the existing or newly created PostView for the (post, user) pair.
        
        Parameters:
            serializer: The serializer whose `.instance` will be set to the PostView object.
        """
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
        """
        Create or update a user's vote for a post and attach the resulting PostVotes instance to the serializer.
        
        Validates that `value` is either `PostVotes.UPVOTE` or `PostVotes.DOWNVOTE`, then updates an existing vote or creates a new one for the (post, user) pair and assigns it to `serializer.instance`.
        
        Parameters:
            serializer: DRF serializer with `validated_data` containing `post`, `user`, and `value`.
        
        Raises:
            ValidationError: If `value` is not `PostVotes.UPVOTE` or `PostVotes.DOWNVOTE`.
        """
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
        """
        Retrieve the PostVotes instance for the current request user and the `post_id` URL parameter.
        
        Returns:
            PostVotes: The vote object for the given post and authenticated user.
        
        Raises:
            ValidationError: If the request user does not exist or if no vote exists for the (post_id, user) pair.
        """
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
        """
        Return top-level comments for the post identified by the `post_id` URL parameter.
        
        The returned queryset contains Comment objects with no parent (top-level) for the specified post and prefetches the `replies` and `author` relations.
        
        Returns:
            QuerySet[Comment]: Top-level comments for the post with `replies` and `author` prefetched.
        """
        post_id = self.kwargs["post_id"]
        return Comment.objects.filter(post_id=post_id, parent=None).prefetch_related(
            "replies", "author"
        )

    def get_serializer_context(self):
        """
        Provide serializer context with an initial depth indicator for nested comment serialization.
        
        Adds a `current_depth` key set to 0 to the serializer context so serializers can track nesting level when rendering or validating nested comment replies.
        
        Returns:
            dict: The serializer context including `current_depth` set to 0.
        """
        context = super().get_serializer_context()
        context["current_depth"] = 0  # start depth counting
        return context


class CommentRetrieveView(RetrieveAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()
    lookup_field = "id"

    def get_serializer_context(self):
        """
        Provide the serializer context with an initial nesting depth for comment serialization.
        
        The returned context preserves the base serializer context and adds "current_depth" set to 0.
        
        Returns:
            context (dict): Serializer context dictionary with "current_depth" = 0.
        """
        context = super().get_serializer_context()
        context["current_depth"] = 0
        return context


class CommentDestroyView(DestroyAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()
    lookup_field = "id"

    def perform_destroy(self, instance):
        """
        Delete the provided comment instance if the requesting user is its author.
        
        Parameters:
            instance (Comment): The comment instance to delete.
        
        Raises:
            ValidationError: If the request does not contain a user_id or the user_id does not correspond to an existing User.
            PermissionDenied: If the requesting user is not the author of the comment.
        """
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
