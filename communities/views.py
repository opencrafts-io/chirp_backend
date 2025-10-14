from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    QuerySet,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response

from communities.permissions import IsCommunityModerator, IsCommunitySuperMod
from event_bus.models.gossip_monger_notification_payload import (
    GOSSIP_MONGER_EXCHANGE,
    GOSSIP_MONGER_ROUTING_KEY,
    GossipMongerNotificationPayLoad,
)
from event_bus.publisher import publish
from users.models import User
from .models import Community, CommunityMembership
from .serializers import (
    CommunityMembershipSerializer,
    CommunitySerializer,
)
from django.db.models import Q
from django.utils import timezone


class CommunityListView(ListAPIView):
    """List all public communitys or communitys user is a member of"""

    serializer_class = CommunitySerializer
    queryset = Community.objects.all()


class CommunityCreateView(CreateAPIView):
    serializer_class = CommunitySerializer
    queryset = Community.objects.all()

    def perform_create(self, serializer: CommunitySerializer):
        # Get the user id
        """
        Create a Community instance using the authenticated user from the request context as the creator.

        Validates that `request.user_id` is present and corresponds to an existing User, then saves the provided serializer with that User assigned to the `creator` field.

        Parameters:
            serializer (CommunitySerializer): Serializer containing community data to be saved.

        Raises:
            ValidationError: If `request.user_id` is missing or empty, or if no User exists with the given `user_id`.
        """
        user_id = self.request.user_id or None
        if user_id is None or user_id == "":
            raise ValidationError(
                f"Failed to parse your information from request context"
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError(f"User with id {user_id} does not exist")

        community = serializer.save(creator=user)
        notification: GossipMongerNotificationPayLoad = GossipMongerNotificationPayLoad(
            headings={"en": f"Your community {community.name}, is ready"},
            contents={
                "en": f"The community {community.name} you’ve created is now live!"
                + " Join now and start building meaningful connections, share your ideas, and grow your network. Tap to explore!"
            },
            subtitle={"en": "Welcome to your new community!"},
            target_user_id=str(user.user_id),
            buttons=None,
            include_external_user_ids=[],
            android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
            ios_sound="hangout",
            big_picture=None,
            large_icon=None,
            small_icon=None,
            url=f"academia://communities/{community.id}",
        )
        publish(
            GOSSIP_MONGER_EXCHANGE, GOSSIP_MONGER_ROUTING_KEY, notification.to_json()
        )


class CommunityRetrieveView(RetrieveAPIView):
    serializer_class = CommunitySerializer
    lookup_field = "id"
    lookup_url_kwarg = "community_id"
    queryset = Community.objects.all()

    def get_queryset(self) -> QuerySet[Community]:
        """
        Return the queryset of Community objects with the related creator preselected for query optimization.

        Returns:
            QuerySet[Community]: A queryset of Community instances with the `creator` relation loaded via select_related.
        """
        return super().get_queryset().select_related("creator")


class CommunityUpdateView(UpdateAPIView):
    serializer_class = CommunitySerializer
    queryset = Community.objects.all()
    permission_classes = [IsCommunityModerator]
    lookup_field = "id"
    lookup_url_kwarg = "community_id"


class CommunityDestroyView(DestroyAPIView):
    permission_classes = [IsCommunitySuperMod]
    serializer_class = CommunitySerializer
    queryset = Community.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "community_id"


class CommunitySearchView(ListAPIView):
    """Search communities by its name or description."""

    serializer_class = CommunitySerializer

    def get_queryset(self) -> QuerySet[Community]:
        """
        Return communities whose name or description contains the request's "q" query parameter.

        Reads the "q" GET parameter from the request (empty string if missing) and returns a QuerySet of Community objects whose name or description contains that value (case-insensitive). The returned queryset is ordered by community name and includes the related creator for efficient access.

        Returns:
            QuerySet[Community]: Filtered and ordered queryset of communities with creator relation selected.
        """
        q = self.request.GET.get("q", "").strip()
        return (
            Community.objects.filter(Q(description__icontains=q) | Q(name__icontains=q))
            .select_related("creator")
            .order_by("name")
        )


# Community memberships
class CommunityMembershipApiView(ListAPIView):
    """
    Returns a list of all memberships belonging to a certain
    community specified by the role query param to specify the role

    The community is to be passed as a path parameter
    """

    serializer_class = CommunityMembershipSerializer

    def get_queryset(self) -> QuerySet[CommunityMembership]:
        """
        Builds the queryset of CommunityMembership objects for the community identified in the URL, applying optional role and banned filters.

        Reads the `role` and `banned` query parameters from the request. `role` accepts aliases: `"superman"` -> `"super-mod"`, `"mods"` -> `"moderator"`; if `role` is not provided an empty role parameter means no role filtering, otherwise unknown values default to `"member"`. `banned` accepts `"true"`, `"1"`, `"false"`, or `"0"` (case-insensitive); when omitted the banned state is not filtered. The returned queryset includes related `community`, `user`, and `banned_by` objects for efficient access.

        Returns:
            QuerySet[CommunityMembership]: Memberships for the specified community with related fields selected.
        """
        role_param = self.request.GET.get("role", "").strip()
        banned_param = self.request.GET.get("banned", "").strip().lower()

        # Sanitize role
        def sanitize_role(role: str) -> str:
            """
            Normalize a role alias to a canonical community role name.

            Parameters:
                role (str): Role string to normalize (case-insensitive).

            Returns:
                str: `'super-mod'` if `role` is "superman", `'moderator'` if `role` is "mods", `'member'` otherwise.
            """
            match role.lower():
                case "superman":
                    return "super-mod"
                case "mods":
                    return "moderator"
            return "member"

        role = sanitize_role(role_param)

        # Start queryset
        queryset = CommunityMembership.objects.filter(
            community_id=self.kwargs.get("community_id")
        )

        # Filter by role if provided
        if role_param:
            queryset = queryset.filter(role=role)

        # Filter by banned status if provided
        if banned_param in {"true", "1"}:
            queryset = queryset.filter(banned=True)
        elif banned_param in {"false", "0"}:
            queryset = queryset.filter(banned=False)
        # else: ignore banned filter if not provided

        return queryset.select_related(
            "community",
            "user",
            "banned_by",
        )


class PersonalCommunityMembershipsApiView(ListAPIView):
    """
    Returns a list of all personal memberships
    """

    serializer_class = CommunityMembershipSerializer

    def get_queryset(self) -> QuerySet[CommunityMembership]:
        try:
            user_id = self.request.user_id or None

            if user_id is None or user_id == "":
                raise ValidationError(
                    f"Failed to parse your information from request context"
                )
            user = User.objects.get(user_id=user_id)

            return CommunityMembership.objects.filter(user=user).select_related(
                "community", "user", "banned_by"
            )
        except User.DoesNotExist:
            raise ValidationError("User does not exist!")
        except Exception as e:
            raise e


class PersonalCommunityMembershipForCommunityApiView(RetrieveAPIView):
    """
    Returns a community membership
    """

    serializer_class = CommunityMembershipSerializer
    lookup_url_kwarg = "community_id"
    lookup_field = "community"

    def get_queryset(self) -> QuerySet[CommunityMembership]:
        try:
            user_id = self.request.user_id or None
            community_id = self.kwargs.get("community_id")

            if user_id is None or user_id == "":
                raise ValidationError(
                    f"Failed to parse your information from request context"
                )
            user = User.objects.get(user_id=user_id)

            return CommunityMembership.objects.filter(
                user=user, community__id=community_id
            ).select_related("community", "user", "banned_by")
        except User.DoesNotExist:
            raise ValidationError("User does not exist!")
        except Exception as e:
            raise e


class CommunityPostableView(ListAPIView):
    serializer_class = CommunitySerializer

    def get_queryset(self) -> QuerySet[Community]:
        """
        Return the communities the requesting user can post to.

        Filters communities where the requesting user has a membership that is not banned, selects the creator relation for performance, ensures distinct results, and orders by community name.

        Returns:
            QuerySet[Community]: QuerySet of Community objects the user can post in (non-banned memberships), with `creator` selected, distinct, ordered by name.

        Raises:
            ValidationError: If `request.user_id` is missing or empty.
            User.DoesNotExist: If no User exists with the provided `user_id`.
        """
        try:
            user_id = self.request.user_id or None

            if user_id is None or user_id == "":
                raise ValidationError(
                    f"Failed to parse your information from request context"
                )
            user = User.objects.get(user_id=user_id)

            return (
                Community.objects.filter(
                    community_memberships__user=user,
                    community_memberships__banned=False,
                )
                .select_related("creator")
                .distinct()
                .order_by("name")
            )

        except Exception as e:
            raise e


class CommunityBanUserView(UpdateAPIView):
    """
    Ban or unban a user from a community based on the `action` query param:
    ?action=ban  → ban the user
    ?action=unban → unban the user

    Optionally, provide a `reason` query param when banning:
    ?reason=Spamming
    """

    serializer_class = CommunityMembershipSerializer

    def get_queryset(self):
        """
        Get the queryset of CommunityMembership objects for the community specified by the `community_id` URL kwarg.

        Returns:
            QuerySet: CommunityMembership queryset filtered by the `community_id` URL parameter.
        """
        community_id = self.kwargs.get("community_id")
        return CommunityMembership.objects.filter(community_id=community_id)

    def perform_update(self, serializer: CommunityMembershipSerializer):
        """
        Ban or unban a community membership based on the request's `action` query parameter.

        Validates the requesting user, enforces that a user cannot ban/unban themselves and that super-mods cannot be targeted, and then applies the requested action. When banning, records who performed the ban, the reason, and a timestamp; when unbanning, clears those fields.

        Parameters:
            serializer (CommunityMembershipSerializer): Serializer whose `instance` is the membership to update.

        Returns:
            CommunityMembership: The membership instance after the operation; returns the existing membership if no state change was required.

        Raises:
            ValidationError: If the request user cannot be resolved, the `action` parameter is missing/invalid, an attempt is made to act on oneself, or an attempt is made to act on a super-mod.
        """
        user_id = self.request.user_id or None
        if not user_id:
            raise ValidationError(
                {"error": "Failed to parse your information from request context"}
            )

        current_user = User.objects.get(user_id=user_id)
        membership = serializer.instance

        action = self.request.query_params.get("action")
        if action not in ("ban", "unban"):
            raise ValidationError(
                {"error": "Invalid action. Must be 'ban' or 'unban'."}
            )

        # Prevent self ban/unban
        if membership.user == current_user:
            raise ValidationError(
                {"error": f"Cannot {action} yourself from the community"}
            )

        # Protect super-mods
        if membership.role == "super-mod":
            raise ValidationError(
                {"error": f"You cannot {action} a super-mod from the community"}
            )

        if action == "ban":
            if membership.banned:
                return membership  # Already banned
            reason = self.request.query_params.get("reason", "No reason provided")
            serializer.save(
                banned=True,
                banned_by=current_user,
                banning_reason=reason,
                banned_at=timezone.now(),
            )
            notification: GossipMongerNotificationPayLoad = (
                GossipMongerNotificationPayLoad(
                    headings={
                        "en": f"You were banned from {membership.community__name}"
                    },
                    contents={
                        "en": f"You have been banned for {reason} and you will not be able to make any more posts"
                        + " on the community"
                    },
                    subtitle={"en": "Time out"},
                    target_user_id=str(user.user_id),
                    buttons=None,
                    include_external_user_ids=[],
                    android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
                    ios_sound="hangout",
                    big_picture=None,
                    large_icon=None,
                    small_icon=None,
                    url=f"academia://communities/{community.id}",
                )
            )
            publish(
                GOSSIP_MONGER_EXCHANGE,
                GOSSIP_MONGER_ROUTING_KEY,
                notification.to_json(),
            )

        else:  # unban
            if not membership.banned:
                return membership
            serializer.save(
                banned=False,
                banned_by=None,
                banning_reason=None,
                banned_at=None,
            )
            notification: GossipMongerNotificationPayLoad = (
                GossipMongerNotificationPayLoad(
                    headings={
                        "en": f"You were unbanned from {membership.community__name}"
                    },
                    contents={
                        "en": f"You have been unbanned and you will now be able to make more posts"
                        + " on the community"
                    },
                    subtitle={"en": "Welcome back"},
                    target_user_id=user_id,
                    buttons=None,
                    include_external_user_ids=[],
                    android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
                    ios_sound="hangout",
                    big_picture=None,
                    large_icon=None,
                    small_icon=None,
                    url=None,
                )
            )
            publish(
                GOSSIP_MONGER_EXCHANGE,
                GOSSIP_MONGER_ROUTING_KEY,
                notification.to_json(),
            )


class CommunityJoinView(CreateAPIView):
    """
    Allows a user to join a community.
    """

    serializer_class = CommunityMembershipSerializer

    def create(self, request, *args, **kwargs):
        """
        Create or retrieve a community membership for the requesting user.

        Creates a CommunityMembership for the user identified by request.user_id in the community specified by `community_id` URL kwarg, or returns the existing membership if present. If the existing membership is banned, the request is rejected.

        Returns:
            Response: Serialized CommunityMembership data; HTTP 201 if a new membership was created, HTTP 200 if an existing (non-banned) membership was returned, HTTP 400 if the request is missing `user_id`, HTTP 404 if the user or community does not exist, HTTP 403 if the user is banned from the community.
        """
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "Failed to parse your information from request context"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with id {user_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        community_id = self.kwargs.get("community_id")
        try:
            community = Community.objects.get(id=community_id)
        except Community.DoesNotExist:
            return Response(
                {"error": "Community does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        membership, created = CommunityMembership.objects.get_or_create(
            community=community, user=user, defaults={"role": "member"}
        )

        if not created and membership.banned:
            return Response(
                {"error": "You are banned from this community."},
                status=status.HTTP_403_FORBIDDEN,
            )

        notification: GossipMongerNotificationPayLoad = GossipMongerNotificationPayLoad(
            headings={"en": f"Welcome to {community.name}!"},
            contents={
                "en": f"Congratulations on joining {community.name}! 🎉 "
                "You're now part of a community where you can share your ideas, "
                "connect with like-minded individuals, and grow together. "
                "Tap to explore and get started!"
            },
            subtitle={"en": "Your journey starts here!"},
            target_user_id=user_id,
            buttons=None,
            include_external_user_ids=[],
            android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
            ios_sound="hangout",
            big_picture=None,
            large_icon=None,
            small_icon=None,
            url=f"academia:///communities/{community.id}",
        )

        publish(
            GOSSIP_MONGER_EXCHANGE,
            GOSSIP_MONGER_ROUTING_KEY,
            notification.to_json(),
        )

        serializer = self.get_serializer(membership)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(serializer.data, status=response_status)


class CommunityLeaveView(DestroyAPIView):
    serializer_class = CommunityMembershipSerializer

    def delete(self, request, *args, **kwargs):
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            return Response(
                {"error": "Failed to parse your information from request context"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with id {user_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        community_id = self.kwargs.get("community_id")
        try:
            community = Community.objects.get(id=community_id)
        except Community.DoesNotExist:
            return Response(
                {"error": "Community does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            membership = CommunityMembership.objects.get(community=community, user=user)
        except CommunityMembership.DoesNotExist:
            return Response(
                {"error": "You are not a member of this community"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership.delete()

        notification: GossipMongerNotificationPayLoad = GossipMongerNotificationPayLoad(
            headings={"en": f"Sorry to see you go, @{user.username}!"},
            contents={
                "en": f"You’ve left the {community.name} community. We’re sad to see you go, but we understand. "
                "If you ever change your mind, the community will always be here for you. "
                "Stay connected, and best of luck on your journey ahead!"
            },
            subtitle={"en": "Goodbye, for now."},
            target_user_id=user_id,
            buttons=None,
            include_external_user_ids=[],
            android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
            ios_sound="hangout",
            big_picture=None,
            large_icon=None,
            small_icon=None,
            url=f"academia:///communities/{community.id}",
        )

        publish(
            GOSSIP_MONGER_EXCHANGE,
            GOSSIP_MONGER_ROUTING_KEY,
            notification.to_json(),
        )

        return Response(
            {"detail": "You have successfully left the community."},
            status=status.HTTP_204_NO_CONTENT,
        )
