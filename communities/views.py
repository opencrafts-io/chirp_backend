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
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from communities.permissions import IsCommunityModerator, IsCommunitySuperMod
from users.models import User
from .models import Community, CommunityMembership
from .serializers import (
    CommunityMembershipSerializer,
    CommunitySerializer,
    UnifiedCommunitySerializer,
)
from django.db.models import Q
from django.utils import timezone
from .models import InviteLink
from .serializers import InviteLinkSerializer


class CommunityListView(ListAPIView):
    """List all public communitys or communitys user is a member of"""

    serializer_class = CommunitySerializer
    queryset = Community.objects.all()


class CommunityCreateView(CreateAPIView):
    serializer_class = CommunitySerializer
    queryset = Community.objects.all()

    def perform_create(self, serializer: CommunitySerializer):
        # Get the user id
        user_id = self.request.user_id or None
        if user_id is None or user_id == "":
            raise ValidationError(
                f"Failed to parse your information from request context"
            )

        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            raise ValidationError(f"User with id {user_id} does not exist")

        serializer.save(creator=user)


class CommunityRetrieveView(RetrieveAPIView):
    serializer_class = CommunitySerializer
    lookup_field = "id"
    lookup_url_kwarg = "community_id"
    queryset = Community.objects.all()

    def get_queryset(self) -> QuerySet[Community]:
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
        role_param = self.request.GET.get("role", "").strip()
        banned_param = self.request.GET.get("banned", "").strip().lower()

        # Sanitize role
        def sanitize_role(role: str) -> str:
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


class PersonalCommunityMembershipApiView(ListAPIView):
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


class CommunityPostableView(ListAPIView):
    serializer_class = CommunitySerializer

    def get_queryset(self) -> QuerySet[Community]:
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
        community_id = self.kwargs.get("community_id")
        return CommunityMembership.objects.filter(community_id=community_id)

    def perform_update(self, serializer: CommunityMembershipSerializer):
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
        else:  # unban
            if not membership.banned:
                return membership
            serializer.save(
                banned=False,
                banned_by=None,
                banning_reason=None,
                banned_at=None,
            )


class CommunityJoinView(CreateAPIView):
    """
    Allows a user to join a community.
    """

    serializer_class = CommunityMembershipSerializer

    def create(self, request, *args, **kwargs):
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

        serializer = self.get_serializer(membership)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(serializer.data, status=response_status)


class CommunityLeaveView(DestroyAPIView):
    serializer_class = CommunityMembershipSerializer
    lookup_url_kwarg = "membership_id"
    lookup_field = "id"
    queryset = CommunityMembership.objects.all()
