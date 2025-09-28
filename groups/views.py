from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from users.models import User
from .models import Group
from .serializers import GroupSerializer, UnifiedGroupSerializer
from django.db.models import Q
from django.core.exceptions import ValidationError
from .models import InviteLink
from .serializers import InviteLinkSerializer


class GroupListView(ListAPIView):
    """List all public groups or groups user is a member of"""

    serializer_class = GroupSerializer
    queryset = Group.objects.all()


class GroupCreateView(CreateAPIView):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()

    def perform_create(self, serializer: GroupSerializer):
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


class GroupRetrieveView(RetrieveAPIView):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    lookup_field = "id"


class GroupUpdateView(UpdateAPIView):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    lookup_field = "id"


class GroupDestroyView(DestroyAPIView):
    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    lookup_field = "id"

    # def get(self, request):
    #     if not hasattr(request, 'user_id') or not request.user_id:
    #         return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    #
    #     user_id = request.user_id
    #
    #     public_groups = Group._default_manager.filter(is_private=False)
    #     if public_groups.exists():
    #         public_groups = list(public_groups)
    #     else:
    #         public_groups = []
    #     user_groups = Group._default_manager.filter(
    #         Q(members__contains=[user_id]) |  # type: ignore
    #         Q(moderators__contains=[user_id]) |  # type: ignore
    #         Q(creator_id=user_id)
    #     ).distinct()
    #     if user_groups.exists():
    #         user_groups = list(user_groups)
    #     else:
    #         user_groups = []
    #
    #     # Combine and remove duplicates
    #     all_groups = list(public_groups) + list(user_groups)
    #     unique_groups = list({group.id: group for group in all_groups}.values())
    #
    #     # serializer = UnifiedGroupSerializer(unique_groups, many=True, context={'request': request, 'user_id': user_id})
    #     return Response(serializer.data)


class GroupPostableView(APIView):
    """Get all groups where the user can post (for post creation dropdown)"""

    def post(self, request):
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = request.user_id

        all_groups = Group._default_manager.all()

        postable_groups = []
        for group in all_groups:
            if group.is_member(user_id):
                if group.can_post(user_id):
                    postable_groups.append(group)

        serializer = UnifiedGroupSerializer(
            postable_groups, many=True, context={"request": request, "user_id": user_id}
        )
        return Response(serializer.data)


# class GroupCreateView(APIView):
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
#         serializer = GroupSerializer(data=clean_data, context={'request': request})
#         if serializer.is_valid():
#             group = serializer.save()
#
#             logo_file = request.FILES.get('logo')
#             if logo_file:
#                 GroupImage._default_manager.create(
#                     group=group,
#                     image_type='logo',
#                     file=logo_file
#                 )
#
#             banner_file = request.FILES.get('banner')
#             if banner_file:
#                 GroupImage._default_manager.create(
#                     group=group,
#                     image_type='banner',
#                     file=banner_file
#                 )
#
#             response_serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': user_id})
#             return Response(response_serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupDetailView(APIView):
    """View community details"""

    def get(self, request, group_id):
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not group.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = UnifiedGroupSerializer(
            group, context={"request": request, "user_id": request.user_id}
        )
        return Response(serializer.data)


class GroupDetailWithUserView(APIView):
    """View community details with user_id in request body"""

    def post(self, request, group_id):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required in request body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not group.can_view(user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = UnifiedGroupSerializer(
            group, context={"request": request, "user_id": user_id}
        )
        return Response(serializer.data)

    def put(self, request, group_id):
        """Update group details and images"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id
        can_mod = group.can_moderate(user_id)
        is_creator = user_id == str(group.creator.user_id) if group.creator else False
        is_in_moderators = group.is_moderator(user_id)

        if not can_mod:
            return Response(
                {
                    "error": "Access denied",
                    "debug": {
                        "user_id": user_id,
                        "group_creator": str(group.creator.user_id) if group.creator else None,
                        "is_creator": is_creator,
                        "is_in_moderators": is_in_moderators,
                        "can_moderate": can_mod,
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        serializer = GroupSerializer(
            group, data=data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            group = serializer.save()

            logo_file = request.FILES.get("logo")
            banner_file = request.FILES.get("banner")

            if logo_file:
                existing_logo = GroupImage._default_manager.filter(
                    group=group, image_type="logo"
                ).first()
                if existing_logo:
                    existing_logo.delete()

                GroupImage._default_manager.create(
                    group=group, image_type="logo", file=logo_file
                )

            if banner_file:
                existing_banner = GroupImage._default_manager.filter(
                    group=group, image_type="banner"
                ).first()
                if existing_banner:
                    existing_banner.delete()

                GroupImage._default_manager.create(
                    group=group, image_type="banner", file=banner_file
                )

            response_serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": request.user_id}
            )
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupJoinView(APIView):
    """Join a community"""

    def post(self, request, group_id):
        user_name = request.data.get("user_name")
        user_id = request.data.get("user_id")

        if not user_name or not user_id:
            return Response(
                {"error": "user_name and user_id are required in request body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            group.self_join(user_id, user_name)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UnifiedGroupSerializer(
            group, context={"request": request, "user_id": user_id}
        )
        return Response(
            {"message": "Successfully joined the community", "group": serializer.data},
            status=status.HTTP_200_OK,
        )


class GroupLeaveView(APIView):
    """Leave a community"""

    def post(self, request, group_id):
        user_id = request.data.get("user_id")
        user_name = request.data.get("user_name")

        if not user_id:
            return Response(
                {"error": "user_id is required in request body"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if user_id == str(group.creator.user_id) if group.creator else False:
            return Response(
                {"error": "Creator cannot leave the community"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove from moderators if present
        try:
            membership = group.group_memberships.get(user__user_id=user_id)
            membership.delete()
        except:
            pass

        group.save()

        # Delete GroupMembership record
        try:
            from users.models import User
            from groups.models import GroupMembership

            user = User._default_manager.get(user_id=user_id)
            GroupMembership._default_manager.filter(group=group, user=user).delete()
        except:
            pass

        return Response({"message": "Successfully left the community"})


class GroupModerationView(APIView):
    """Moderate community members and content"""

    def post(self, request, group_id):
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user performing the action is a moderator or creator
        if not group.can_moderate(user_id):
            return Response(
                {
                    "error": "Only moderators and creators can perform moderation actions"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            if action == "add_member":
                group.add_member(member_id, member_name or member_id, user_id)
                message = f"Added {member_id} as member"
            elif action == "remove_member":
                group.remove_member(member_id, user_id)
                message = f"Removed {member_id} as member"
            elif action == "add_moderator":
                group.add_moderator(member_id, member_name or member_id, user_id)
                message = f"Added {member_id} as moderator"
            elif action == "remove_moderator":
                group.remove_moderator(member_id, user_id)
                message = f"Removed {member_id} as moderator"
            elif action == "ban":
                group.ban_user(member_id, member_name or member_id, user_id)
                message = f"Banned {member_id}"
            elif action == "unban":
                group.unban_user(member_id, user_id)
                message = f"Unbanned {member_id}"
            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

            serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "group": serializer.data})

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupAdminView(APIView):
    """Moderator-only community management"""

    def post(self, request, group_id):
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user performing the action is a moderator or creator
        if not group.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can perform admin actions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            if action == "add_moderator":
                group.add_moderator(member_id, member_name or member_id, user_id)
                message = f"Added {member_id} as moderator"
            elif action == "remove_moderator":
                group.remove_moderator(member_id, user_id)
                message = f"Removed {member_id} as moderator"
            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

            serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "group": serializer.data})

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupSettingsView(APIView):
    """Update community settings"""

    def put(self, request, group_id):
        """Update group settings (only moderators can do this)"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id

        if not group.is_moderator(user_id) and user_id != str(group.creator.user_id) if group.creator else True:
            return Response(
                {"error": "Only moderators can update group settings"},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_fields = ["name", "description", "private"]
        for field in allowed_fields:
            if field in request.data:
                setattr(group, field, request.data[field])

        if "logo" in request.FILES:
            group.logo = request.FILES["logo"]
        if "banner" in request.FILES:
            group.banner = request.FILES["banner"]

        group.save()

        serializer = UnifiedGroupSerializer(
            group, context={"request": request, "user_id": request.user_id}
        )
        return Response(serializer.data)


class GroupRulesView(APIView):
    """Manage community rules/guidelines"""

    def get(self, request, group_id):
        """Get all community rules with full group object"""
        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = getattr(request, "user_id", None)
        if user_id and not group.can_view(user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = UnifiedGroupSerializer(
            group, context={"request": request, "user_id": user_id}
        )
        return Response(serializer.data)

    def post(self, request, group_id):
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is a moderator or creator
        if not group.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can add rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            added_count = 0
            for rule_item in rule:
                if rule_item and str(rule_item).strip():
                    group.add_rule(str(rule_item).strip(), user_id)
                    added_count += 1

            if added_count == 1:
                message = "Rule added successfully"
            else:
                message = f"{added_count} rules added successfully"

            serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "group": serializer.data})
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, group_id):
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is a moderator or creator
        if not group.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can update rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            group.update_rules(rules, user_id)

            serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": user_id}
            )
            return Response(
                {"message": "Rules updated successfully", "group": serializer.data}
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, group_id):
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is a moderator or creator
        if not group.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can remove rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            removed_count = 0
            for rule_item in rule:
                if rule_item and str(rule_item).strip():
                    try:
                        group.remove_rule(str(rule_item).strip(), user_id)
                        removed_count += 1
                    except ValidationError:
                        # Rule not found, continue with others
                        pass

            if removed_count == 1:
                message = "Rule removed successfully"
            else:
                message = f"{removed_count} rules removed successfully"

            serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": user_id}
            )
            return Response({"message": message, "group": serializer.data})
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupRuleEditView(APIView):
    """Edit a specific rule by index (only moderators can do this)"""

    def patch(self, request, group_id, rule_index):
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not group.can_moderate(user_id):
            return Response(
                {"error": "Only moderators and creators can edit rules"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            rule_index = int(rule_index)
            current_rules = group.get_rules()

            if rule_index < 0 or rule_index >= len(current_rules):
                return Response(
                    {"error": "Invalid rule index"}, status=status.HTTP_400_BAD_REQUEST
                )

            current_rules[rule_index] = str(new_rule).strip()
            group.guidelines = current_rules
            group.save()

            serializer = UnifiedGroupSerializer(
                group, context={"request": request, "user_id": user_id}
            )
            return Response(
                {"message": "Rule updated successfully", "group": serializer.data}
            )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid rule index"}, status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupMembersPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 50


class GroupMembersView(APIView):
    """List all members in a community with pagination"""

    def get(self, request, group_id):
        """Get paginated list of members in the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not group.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            memberships = group.group_memberships.filter(role="member").select_related("user")
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
            member_list = []

        # Paginate the results
        paginator = GroupMembersPagination()
        paginated_members = paginator.paginate_queryset(member_list, request)

        return paginator.get_paginated_response(
            {"count": len(member_list), "members": paginated_members}
        )


class GroupSearchView(APIView):
    """Search communities by name or description."""

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        page_size = min(int(request.GET.get("page_size", 20)), 100)

        if len(q) < 2:
            return Response(
                {
                    "error": "Query must be at least 2 characters",
                    "results": [],
                    "count": 0,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only return groups the user can view if authenticated
        user_id = getattr(request, "user_id", None)
        base_qs = Group._default_manager.all()
        if user_id:
            base_qs = base_qs.filter(
                Q(private=False)
                | Q(group_memberships__user__user_id=user_id)
                | Q(creator__user_id=user_id)
            )
        else:
            base_qs = base_qs.filter(private=False)

        qs = base_qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        ).order_by("-created_at")

        from chirp.pagination import StandardResultsSetPagination

        paginator = StandardResultsSetPagination()
        paginator.page_size = page_size
        page = paginator.paginate_queryset(qs, request)
        serializer = UnifiedGroupSerializer(
            page, many=True, context={"request": request, "user_id": user_id}
        )
        return paginator.get_paginated_response(serializer.data)


class GroupModeratorsView(APIView):
    """List all moderators in a community with pagination"""

    def get(self, request, group_id):
        """Get paginated list of moderators in the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not group.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            memberships = group.group_memberships.filter(
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
            moderator_list = []
            if group.creator:
                moderator_list.append(
                    {"user_id": str(group.creator.user_id), "user_name": group.creator.name, "role": "creator"}
                )

        # Paginate the results
        paginator = GroupMembersPagination()
        paginated_moderators = paginator.paginate_queryset(moderator_list, request)

        return paginator.get_paginated_response(
            {"count": len(moderator_list), "moderators": paginated_moderators}
        )


class GroupBannedUsersView(APIView):
    """List all banned users in a community with pagination"""

    def get(self, request, group_id):
        """Get paginated list of banned users in the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not group.can_view(request.user_id):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get banned users data
        banned_list = []

        # Paginate the results
        paginator = GroupMembersPagination()
        paginated_banned = paginator.paginate_queryset(banned_list, request)

        return paginator.get_paginated_response(
            {"count": len(banned_list), "banned_users": paginated_banned}
        )


class GroupDeleteView(APIView):
    """Delete a community (only moderators can do this)"""

    def delete(self, request, group_id):
        """Delete the group (only creator can do this)"""
        user_id = request.GET.get("user_id")

        if not user_id:
            return Response(
                {
                    "error": "user_id query parameter is required",
                    "example": "DELETE /groups/{group_id}/?user_id=default_user_123",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if user_id != str(group.creator.user_id) if group.creator else True:
            return Response(
                {"error": "Only the group creator can delete this group"},
                status=status.HTTP_403_FORBIDDEN,
            )

        group_name = group.name
        group_id_value = group.id

        group.delete()

        return Response(
            {
                "message": f'Group "{group_name}" has been successfully deleted',
                "deleted_group_id": group_id_value,
            },
            status=status.HTTP_200_OK,
        )


class InviteLinkCreateView(APIView):
    """Create invite links for a community (moderators only)"""

    def post(self, request, group_id):
        """Create a new invite link"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)  # type: ignore
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id

        if not group.is_moderator(user_id) and user_id != str(group.creator.user_id) if group.creator else True:
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
            "group": group.id,
            "created_by": user_id,
            "created_by_name": getattr(request, "user_name", f"User {user_id}"),
            "expiration_hours": expiration_hours,
        }

        serializer = InviteLinkSerializer(data=invite_data)
        if serializer.is_valid():
            invite_link = serializer.save()

            invite_url = f"https://qachirp.opencrafts.io/groups/{group_id}/join/invite/{invite_link.token}/"  # type: ignore

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

    def post(self, request, group_id, invite_token):
        """Join group using invite link"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            invite_link = InviteLink._default_manager.get(
                token=invite_token, group=group
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

        if group.is_member(user_id):
            return Response(
                {"message": "Already a member of this community"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_id in group.banned_users:
            return Response(
                {"error": "You are banned from this community"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            group.add_member(user_id, user_name, user_id)

            invite_link.mark_as_used(user_id, user_name)

            return Response(
                {
                    "message": "Successfully joined community using invite link",
                    "group": UnifiedGroupSerializer(
                        group, context={"request": request, "user_id": request.user_id}
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InviteLinkListView(APIView):
    """List all invite links for a community (moderators only)"""

    def get(self, request, group_id):
        """Get all invite links for the community"""
        if not hasattr(request, "user_id") or not request.user_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response(
                {"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user_id = request.user_id

        if not group.is_moderator(user_id) and user_id != str(group.creator.user_id) if group.creator else True:
            return Response(
                {"error": "Only moderators can view invite links"},
                status=status.HTTP_403_FORBIDDEN,
            )

        invite_links = InviteLink._default_manager.filter(group=group).order_by(
            "-created_at"
        )
        serializer = InviteLinkSerializer(invite_links, many=True)

        return Response({"group_name": group.name, "invite_links": serializer.data})
