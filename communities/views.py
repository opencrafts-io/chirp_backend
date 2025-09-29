from rest_framework import status
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

from posts import serializers
from users.models import User
from .models import Community, CommunityMembership
from .serializers import (
    CommunityMembershipSerializer,
    CommunitySerializer,
    UnifiedCommunitySerializer,
)
from django.db.models import Q
from django.core.exceptions import ValidationError
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
    queryset = Community.objects.all()
    lookup_field = "id"


class CommunityUpdateView(UpdateAPIView):
    serializer_class = CommunitySerializer
    queryset = Community.objects.all()
    lookup_field = "id"


class CommunityDestroyView(DestroyAPIView):
    serializer_class = CommunitySerializer
    queryset = Community.objects.all()
    lookup_field = "id"


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
        role = self.request.GET.get("role", "").strip()

        def sanitize_role(role: str) -> str:
            match role.lower():
                case "superman":
                    return "super-mod"
                case "mods":
                    return "moderator"
            return "member"

        community_id = self.kwargs.get("community_id")
        return CommunityMembership.objects.filter(
            community_id=community_id, role=sanitize_role(role)
        ).select_related(
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


# class CommunityCreateView(APIView):
#     """Create a new community"""
#
#     def post(self, request):
#         if not hasattr(request, 'user_id') or not request.user_id:
#             return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
#
#         data = request.data.copy()
#
#         clean_data = {}
#         for key, value in data.items():
#             if isinstance(value, list) and len(value) == 1:
#                 clean_data[key] = value[0]
#             else:
#                 clean_data[key] = value
#
#         user_id = clean_data.get('user_id', request.user_id)
#         user_name = clean_data.get('user_name', getattr(request, 'user_name', f"User {request.user_id}"))
#
#         clean_data['creator_id'] = user_id
#         clean_data['creator_name'] = user_name
#
#         if 'is_public' in clean_data:
#             is_public_value = not clean_data.pop('is_public')
#             if isinstance(is_public_value, bool):
#                 is_private_value = not is_public_value
#             else:
#                 is_private_value = not(str(is_public_value).lower() == 'true')
#
#             clean_data['is_private'] = is_private_value
#         clean_data['moderators'] = [str(user_id)]
#         clean_data['moderator_names'] = [str(user_name)]
#         clean_data['members'] = [str(user_id)]
#         clean_data['member_names'] = [str(user_name)]
#
#         serializer = CommunitySerializer(data=clean_data, context={'request': request})
#         if serializer.is_valid():
#             community = serializer.save()
#
#             logo_file = request.FILES.get('logo')
#             if logo_file:
#                 CommunityImage._default_manager.create(
#                     community=community,
#                     image_type='logo',
#                     file=logo_file
#                 )
#
#             banner_file = request.FILES.get('banner')
#             if banner_file:
#                 CommunityImage._default_manager.create(
#                     community=community,
#                     image_type='banner',
#                     file=banner_file
#                 )
#
#             response_serializer = UnifiedCommunitySerializer(community, context={'request': request, 'user_id': user_id})
#             return Response(response_serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommunityDetailView(APIView):
    """View community details"""

    def get(self, request, community_id):
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not community.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = UnifiedCommunitySerializer(
            community, context={"request": request, "user_id": request.user_id}
        )
        return Response(serializer.data)


class CommunityDetailWithUserView(APIView):
    """View community details with user_id in request body"""

    def post(self, request, community_id):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required in request body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not community.can_view(user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = UnifiedCommunitySerializer(
            community, context={"request": request, "user_id": user_id}
        )
        return Response(serializer.data)

    def put(self, request, community_id):
        """Update community details and images"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id
        can_mod = community.can_moderate(user_id)
        is_creator = user_id == community.creator_id
        is_in_moderators = user_id in community.moderators

        if not can_mod:
            return Response(
                {
                    "error": "Access denied",
                    "debug": {
                        "user_id": user_id,
                        "community_creator": community.creator_id,
                        "is_creator": is_creator,
                        "moderators": community.moderators,
                        "is_in_moderators": is_in_moderators,
                        "can_moderate": can_mod,
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        serializer = CommunitySerializer(
            community, data=data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            community = serializer.save()

            logo_file = request.FILES.get("logo")
            banner_file = request.FILES.get("banner")

            if logo_file:
                existing_logo = CommunityImage._default_manager.filter(
                    community=community, image_type="logo"
                ).first()
                if existing_logo:
                    existing_logo.delete()

                CommunityImage._default_manager.create(
                    community=community, image_type="logo", file=logo_file
                )

            if banner_file:
                existing_banner = CommunityImage._default_manager.filter(
                    community=community, image_type="banner"
                ).first()
                if existing_banner:
                    existing_banner.delete()

                CommunityImage._default_manager.create(
                    community=community, image_type="banner", file=banner_file
                )

            response_serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": request.user_id}
            )
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommunityJoinView(APIView):
    """Join a community"""

    def post(self, request, community_id):
        user_name = request.data.get("user_name")
        user_id = request.data.get("user_id")

        if not user_name or not user_id:
            return Response(
                {"error": "user_name and user_id are required in request body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            community.self_join(user_id, user_name)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UnifiedCommunitySerializer(
            community, context={"request": request, "user_id": user_id}
        )
        return Response(
            {
                "message": "Successfully joined the community",
                "community": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CommunityLeaveView(APIView):
    """Leave a community"""

    def post(self, request, community_id):
        user_id = request.data.get("user_id")
        user_name = request.data.get("user_name")

        if not user_id:
            return Response(
                {"error": "user_id is required in request body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if user_id == community.creator_id:
            return Response(
                {"error": "Creator cannot leave the community"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove from moderators if present
        if user_id in community.moderators:
            current_moderators = list(community.moderators)
            current_moderator_names = list(community.moderator_names)
            try:
                index = current_moderators.index(user_id)
                current_moderators.remove(user_id)
                current_moderator_names.pop(index)
                community.moderators = current_moderators
                community.moderator_names = current_moderator_names
            except (ValueError, IndexError):
                pass

        # Remove from members if present
        if user_id in community.members:
            current_members = list(community.members)
            current_member_names = list(community.member_names)
            try:
                index = current_members.index(user_id)
                current_members.remove(user_id)
                current_member_names.pop(index)
                community.members = current_members
                community.member_names = current_member_names
            except (ValueError, IndexError):
                pass

        community.save()

        # Delete CommunityMembership record
        try:
            from users.models import User
            from communitys.models import CommunityMembership

            user = User._default_manager.get(user_id=user_id)
            CommunityMembership._default_manager.filter(
                community=community, user=user
            ).delete()
        except:
            pass

        return Response({"message": "Successfully left the community"})


class CommunityModerationView(APIView):
    """Moderate community members and content"""

    def post(self, request, community_id):
        """Add/remove members, moderators, or ban users"""
        action = request.data.get("action")
        user_id = request.data.get("user_id")  # Moderator/creator performing the action
        member_id = request.data.get("member_id")  # Target user being acted upon
        member_name = request.data.get("member_name")  # Target user's name

        if not action or not user_id:
            return Response(
                {"error": "Action and user_id (moderator/creator) required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action in [
            "add_member",
            "remove_member",
            "add_moderator",
            "remove_moderator",
            "ban",
            "unban",
        ]:
            if not member_id:
                return Response(
                    {"error": "member_id is required for this action"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user performing the action is a moderator or creator
        if not community.can_moderate(user_id):
            return Response(
                {
                    "error": "Only moderators and creators can perform moderation actions"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            if action == "add_member":
                community.add_member(member_id, member_name or member_id, user_id)
                message = f"Added {member_id} as member"
            elif action == "remove_member":
                community.remove_member(member_id, user_id)
                message = f"Removed {member_id} as member"
            elif action == "add_moderator":
                community.add_moderator(member_id, member_name or member_id, user_id)
                message = f"Added {member_id} as moderator"
            elif action == "remove_moderator":
                community.remove_moderator(member_id, user_id)
                message = f"Removed {member_id} as moderator"
            elif action == "ban":
                community.ban_user(member_id, member_name or member_id, user_id)
                message = f"Banned {member_id}"
            elif action == "unban":
                community.unban_user(member_id, user_id)
                message = f"Unbanned {member_id}"
            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

            serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "community": serializer.data})

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CommunityAdminView(APIView):
    """Moderator-only community management"""

    def post(self, request, community_id):
        """Add/remove moderators (only existing moderators can do this)"""
        action = request.data.get("action")
        user_id = request.data.get("user_id")  # Moderator/creator performing the action
        member_id = request.data.get("member_id")  # Target user being acted upon
        member_name = request.data.get("member_name")  # Target user's name

        if not action or not user_id:
            return Response(
                {"error": "Action and user_id (moderator/creator) required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not member_id:
            return Response(
                {"error": "member_id is required for this action"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user performing the action is a moderator or creator
        if not community.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can perform admin actions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            if action == "add_moderator":
                community.add_moderator(member_id, member_name or member_id, user_id)
                message = f"Added {member_id} as moderator"
            elif action == "remove_moderator":
                community.remove_moderator(member_id, user_id)
                message = f"Removed {member_id} as moderator"
            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

            serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "community": serializer.data})

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CommunitySettingsView(APIView):
    """Update community settings"""

    def put(self, request, community_id):
        """Update community settings (only moderators can do this)"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id

        if user_id not in community.moderators and user_id != community.creator_id:
            return Response(
                {"error": "Only moderators can update community settings"},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_fields = ["name", "description", "private"]
        for field in allowed_fields:
            if field in request.data:
                setattr(community, field, request.data[field])

        if "logo" in request.FILES:
            community.logo = request.FILES["logo"]
        if "banner" in request.FILES:
            community.banner = request.FILES["banner"]

        community.save()

        serializer = UnifiedCommunitySerializer(
            community, context={"request": request, "user_id": request.user_id}
        )
        return Response(serializer.data)


class CommunityRulesView(APIView):
    """Manage community rules/guidelines"""

    def get(self, request, community_id):
        """Get all community rules with full community object"""
        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = getattr(request, "user_id", None)
        if user_id and not community.can_view(user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = UnifiedCommunitySerializer(
            community, context={"request": request, "user_id": user_id}
        )
        return Response(serializer.data)

    def post(self, request, community_id):
        """Add rule(s) to the community (only moderators can do this)"""
        user_id = request.data.get("user_id")
        rule = request.data.get("rule")

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not rule:
            return Response(
                {"error": "rule is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(rule, list):
            rule = [rule]

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is a moderator or creator
        if not community.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can add rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            added_count = 0
            for rule_item in rule:
                if rule_item and str(rule_item).strip():
                    community.add_rule(str(rule_item).strip(), user_id)
                    added_count += 1

            if added_count == 1:
                message = "Rule added successfully"
            else:
                message = f"{added_count} rules added successfully"

            serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "community": serializer.data})
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, community_id):
        """Update all community rules (only moderators can do this)"""
        rules = request.data.get("rules")
        user_id = request.data.get("user_id")

        if not isinstance(rules, list):
            return Response(
                {"error": "Rules must be a list"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is a moderator or creator
        if not community.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can update rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            community.update_rules(rules, user_id)

            serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": user_id}
            )
            return Response(
                {"message": "Rules updated successfully", "community": serializer.data}
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, community_id):
        """Remove specific rule(s) from the community (only moderators can do this)"""
        user_id = request.data.get("user_id")
        rule = request.data.get("rule")

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not rule:
            return Response(
                {"error": "rule is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure rule is always treated as a list
        if not isinstance(rule, list):
            rule = [rule]

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is a moderator or creator
        if not community.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can remove rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            removed_count = 0
            for rule_item in rule:
                if rule_item and str(rule_item).strip():
                    try:
                        community.remove_rule(str(rule_item).strip(), user_id)
                        removed_count += 1
                    except ValidationError:
                        # Rule not found, continue with others
                        pass

            if removed_count == 1:
                message = "Rule removed successfully"
            else:
                message = f"{removed_count} rules removed successfully"

            serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "community": serializer.data})
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CommunityRuleEditView(APIView):
    """Edit a specific rule by index (only moderators can do this)"""

    def patch(self, request, community_id, rule_index):
        """Edit a specific rule by its index"""
        user_id = request.data.get("user_id")
        new_rule = request.data.get("rule")

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not new_rule:
            return Response(
                {"error": "Rule content is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not community.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can edit rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            rule_index = int(rule_index)
            current_rules = community.get_rules()

            if rule_index < 0 or rule_index >= len(current_rules):
                return Response(
                    {"error": "Invalid rule index"}, status=status.HTTP_400_BAD_REQUEST
                )

            current_rules[rule_index] = str(new_rule).strip()
            community.rules = current_rules
            community.save()

            serializer = UnifiedCommunitySerializer(
                community, context={"request": request, "user_id": user_id}
            )
            return Response(
                {"message": "Rule updated successfully", "community": serializer.data}
            )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid rule index"}, status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CommunityMembersPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 50


class CommunityMembersView(APIView):
    """List all members in a community with pagination"""

    def get(self, request, community_id):
        """Get paginated list of members in the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not community.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            memberships = community.memberships.filter(role="member").select_related(
                "user"
            )
            member_list = []
            for membership in memberships:
                member_list.append(
                    {
                        "user_id": membership.user.user_id,
                        "user_name": membership.user.user_name,
                        "role": "member",
                    }
                )
        except:
            members = community.members if isinstance(community.members, list) else []
            member_names = (
                community.member_names
                if isinstance(community.member_names, list)
                else []
            )
            moderators = (
                community.moderators if isinstance(community.moderators, list) else []
            )
            creator_id = community.creator_id

            member_list = []

        # Paginate the results
        paginator = CommunityMembersPagination()
        paginated_members = paginator.paginate_queryset(member_list, request)

        return paginator.get_paginated_response(
            {"count": len(member_list), "members": paginated_members}
        )


class CommunityModeratorsView(APIView):
    """List all moderators in a community with pagination"""

    def get(self, request, community_id):
        """Get paginated list of moderators in the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not community.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            memberships = community.memberships.filter(
                role__in=["creator", "moderator"]
            ).select_related("user")
            moderator_list = []
            for membership in memberships:
                moderator_list.append(
                    {
                        "user_id": membership.user.user_id,
                        "user_name": membership.user.user_name,
                        "role": membership.role,
                    }
                )
        except:
            moderators = (
                community.moderators if isinstance(community.moderators, list) else []
            )
            moderator_names = (
                community.moderator_names
                if isinstance(community.moderator_names, list)
                else []
            )
            creator_id = community.creator_id
            creator_name = community.creator_name

            moderator_list = []
            if group.creator:
                moderator_list.append(
                    {
                        "user_id": str(group.creator.user_id),
                        "user_name": group.creator.name,
                        "role": "creator",
                    }
                )

        # Paginate the results
        paginator = CommunityMembersPagination()
        paginated_moderators = paginator.paginate_queryset(moderator_list, request)

        return paginator.get_paginated_response(
            {"count": len(moderator_list), "moderators": paginated_moderators}
        )


class CommunityBannedUsersView(APIView):
    """List all banned users in a community with pagination"""

    def get(self, request, community_id):
        """Get paginated list of banned users in the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not community.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get banned users data
        banned_users = (
            community.banned_users if isinstance(community.banned_users, list) else []
        )
        banned_user_names = (
            community.banned_user_names
            if isinstance(community.banned_user_names, list)
            else []
        )

        # Create banned user objects
        banned_list = []

        # Paginate the results
        paginator = CommunityMembersPagination()
        paginated_banned = paginator.paginate_queryset(banned_list, request)

        return paginator.get_paginated_response(
            {"count": len(banned_list), "banned_users": paginated_banned}
        )


class CommunityDeleteView(APIView):
    """Delete a community (only moderators can do this)"""

    def delete(self, request, community_id):
        """Delete the community (only creator can do this)"""
        user_id = request.GET.get("user_id")

        if not user_id:
            return Response(
                {
                    "error": "user_id query parameter is required",
                    "example": "DELETE /communitys/{community_id}/?user_id=default_user_123",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if user_id != community.creator_id:
            return Response(
                {"error": "Only the community creator can delete this community"},
                status=status.HTTP_403_FORBIDDEN,
            )

        community_name = community.name
        community_id_value = community.id

        community.delete()

        return Response(
            {
                "message": f'Community "{community_name}" has been successfully deleted',
                "deleted_community_id": community_id_value,
            },
            status=status.HTTP_200_OK,
        )


class InviteLinkCreateView(APIView):
    """Create invite links for a community (moderators only)"""

    def post(self, request, community_id):
        """Create a new invite link"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)  # type: ignore
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id

        if user_id not in community.moderators and user_id != community.creator_id:
            return Response(
                {"error": "Only moderators can create invite links"},
                status=status.HTTP_403_FORBIDDEN,
            )

        expiration_hours = request.data.get("expiration_hours", 72)
        if expiration_hours not in [72, 168]:
            return Response(
                {"error": "Invalid expiration time. Choose 72 (hours) or 168 (1 week)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invite_data = {
            "community": community.id,
            "created_by": user_id,
            "created_by_name": getattr(request, "user_name", f"User {user_id}"),
            "expiration_hours": expiration_hours,
        }

        serializer = InviteLinkSerializer(data=invite_data)
        if serializer.is_valid():
            invite_link = serializer.save()

            invite_url = f"https://qachirp.opencrafts.io/communitys/{community_id}/join/invite/{invite_link.token}/"  # type: ignore

            return Response(
                {
                    "message": "Invite link created successfully",
                    "invite_link": InviteLinkSerializer(invite_link).data,
                    "invite_url": invite_url,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InviteLinkJoinView(APIView):
    """Join a community using an invite link"""

    def post(self, request, community_id, invite_token):
        """Join community using invite link"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            invite_link = InviteLink._default_manager.get(
                token=invite_token, community=community
            )
        except InviteLink.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Invalid invite link"}, status=status.HTTP_404_NOT_FOUND
            )

        if not invite_link.can_be_used():
            if invite_link.is_used:
                return Response(
                    {
                        "error": "This invite link has already been used. Kindly request for a new invite link from the community moderator."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif invite_link.is_expired():
                return Response(
                    {
                        "error": "This invite link has expired. Kindly request for a new invite link from the community moderator."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                return Response(
                    {
                        "error": "This invite link cannot be used. Kindly request for a new invite link from the community moderator."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user_id = request.user_id
        user_name = request.data.get(
            "user_name", getattr(request, "user_name", f"User {user_id}")
        )
        user_email = request.data.get("user_email")

        if community.is_member(user_id):
            return Response(
                {"message": "Already a member of this community"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_id in community.banned_users:
            return Response(
                {"error": "You are banned from this community"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            community.add_member(user_id, user_name, user_id)

            invite_link.mark_as_used(user_id, user_name)

            return Response(
                {
                    "message": "Successfully joined community using invite link",
                    "community": UnifiedCommunitySerializer(
                        community,
                        context={"request": request, "user_id": request.user_id},
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InviteLinkListView(APIView):
    """List all invite links for a community (moderators only)"""

    def get(self, request, community_id):
        """Get all invite links for the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            community = Community._default_manager.get(id=community_id)
        except Community.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id

        if user_id not in community.moderators and user_id != community.creator_id:
            return Response(
                {"error": "Only moderators can view invite links"},
                status=status.HTTP_403_FORBIDDEN,
            )

        invite_links = InviteLink._default_manager.filter(community=community).order_by(
            "-created_at"
        )
        serializer = InviteLinkSerializer(invite_links, many=True)

        return Response(
            {"community_name": community.name, "invite_links": serializer.data}
        )
