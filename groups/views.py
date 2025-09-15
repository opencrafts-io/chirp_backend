from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from .models import Group, GroupImage
from .serializers import GroupSerializer, UnifiedGroupSerializer
from django.db.models import Q
from django.core.exceptions import ValidationError
from .models import InviteLink
from .serializers import InviteLinkSerializer

class GroupListView(APIView):
    """List all public groups or groups user is a member of"""

    def get(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = request.user_id

        public_groups = Group._default_manager.filter(is_private=False)
        if public_groups.exists():
            public_groups = list(public_groups)
        else:
            public_groups = []
        user_groups = Group._default_manager.filter(
            Q(members__contains=[user_id]) |  # type: ignore
            Q(moderators__contains=[user_id]) |  # type: ignore
            Q(creator_id=user_id)
        ).distinct()
        if user_groups.exists():
            user_groups = list(user_groups)
        else:
            user_groups = []

        # Combine and remove duplicates
        all_groups = list(public_groups) + list(user_groups)
        unique_groups = list({group.id: group for group in all_groups}.values())

        serializer = UnifiedGroupSerializer(unique_groups, many=True, context={'request': request, 'user_id': user_id})
        return Response(serializer.data)


class GroupPostableView(APIView):
    """Get all groups where the user can post (for post creation dropdown)"""

    def post(self, request):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        all_groups = Group._default_manager.all()

        postable_groups = []
        for group in all_groups:
            if group.is_member(user_id):
                if group.can_post(user_id):
                    postable_groups.append(group)

        serializer = UnifiedGroupSerializer(postable_groups, many=True, context={'request': request, 'user_id': user_id})
        return Response(serializer.data)


class GroupCreateView(APIView):
    """Create a new community"""

    def post(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()

        clean_data = {}
        for key, value in data.items():
            if isinstance(value, list) and len(value) == 1:
                clean_data[key] = value[0]
            else:
                clean_data[key] = value

        user_id = clean_data.get('user_id', request.user_id)
        user_name = clean_data.get('user_name', getattr(request, 'user_name', f"User {request.user_id}"))

        clean_data['creator_id'] = user_id
        clean_data['creator_name'] = user_name

        if 'is_public' in clean_data:
            clean_data['is_private'] = not clean_data.pop('is_public')

        clean_data['moderators'] = [str(user_id)]
        clean_data['moderator_names'] = [str(user_name)]
        clean_data['members'] = [str(user_id)]
        clean_data['member_names'] = [str(user_name)]

        serializer = GroupSerializer(data=clean_data, context={'request': request})
        if serializer.is_valid():
            group = serializer.save()

            logo_file = request.FILES.get('logo')
            if logo_file:
                GroupImage._default_manager.create(
                    group=group,
                    image_type='logo',
                    file=logo_file
                )

            banner_file = request.FILES.get('banner')
            if banner_file:
                GroupImage._default_manager.create(
                    group=group,
                    image_type='banner',
                    file=banner_file
                )

            response_serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': user_id})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupDetailView(APIView):
    """View community details"""

    def get(self, request, group_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': request.user_id})
        return Response(serializer.data)


class GroupDetailWithUserView(APIView):
    """View community details with user_id in request body"""

    def post(self, request, group_id):
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': 'user_id is required in request body'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': user_id})
        return Response(serializer.data)

    def put(self, request, group_id):
        """Update group details and images"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id
        can_mod = group.can_moderate(user_id)
        is_creator = user_id == group.creator_id
        is_in_moderators = user_id in group.moderators

        if not can_mod:
            return Response({
                'error': 'Access denied',
                'debug': {
                    'user_id': user_id,
                    'group_creator': group.creator_id,
                    'is_creator': is_creator,
                    'moderators': group.moderators,
                    'is_in_moderators': is_in_moderators,
                    'can_moderate': can_mod
                }
            }, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        serializer = GroupSerializer(group, data=data, partial=True, context={'request': request})

        if serializer.is_valid():
            group = serializer.save()

            logo_file = request.FILES.get('logo')
            banner_file = request.FILES.get('banner')

            if logo_file:
                existing_logo = GroupImage._default_manager.filter(group=group, image_type='logo').first()
                if existing_logo:
                    existing_logo.delete()

                GroupImage._default_manager.create(
                    group=group,
                    image_type='logo',
                    file=logo_file
                )

            if banner_file:
                existing_banner = GroupImage._default_manager.filter(group=group, image_type='banner').first()
                if existing_banner:
                    existing_banner.delete()

                GroupImage._default_manager.create(
                    group=group,
                    image_type='banner',
                    file=banner_file
                )

            response_serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': request.user_id})
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupJoinView(APIView):
    """Join a community"""

    def post(self, request, group_id):
        user_name = request.data.get('user_name')
        user_id = request.data.get('user_id')

        if not user_name or not user_id:
            return Response({
                'error': 'user_name and user_id are required in request body'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.self_join(user_id, user_name)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': user_id})
        return Response({
            'message': 'Successfully joined the community',
            'group': serializer.data
        }, status=status.HTTP_200_OK)


class GroupLeaveView(APIView):
    """Leave a community"""

    def post(self, request, group_id):
        user_id = request.data.get('user_id')
        user_name = request.data.get('user_name')

        if not user_id:
            return Response({'error': 'user_id is required in request body'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if user_id == group.creator_id:
            return Response({'error': 'Creator cannot leave the community'}, status=status.HTTP_400_BAD_REQUEST)

        # Remove from moderators if present
        if user_id in group.moderators:
            current_moderators = list(group.moderators)
            current_moderator_names = list(group.moderator_names)
            try:
                index = current_moderators.index(user_id)
                current_moderators.remove(user_id)
                current_moderator_names.pop(index)
                group.moderators = current_moderators
                group.moderator_names = current_moderator_names
            except (ValueError, IndexError):
                pass

        # Remove from members if present
        if user_id in group.members:
            current_members = list(group.members)
            current_member_names = list(group.member_names)
            try:
                index = current_members.index(user_id)
                current_members.remove(user_id)
                current_member_names.pop(index)
                group.members = current_members
                group.member_names = current_member_names
            except (ValueError, IndexError):
                pass

        group.save()

        return Response({'message': 'Successfully left the community'})


class GroupModerationView(APIView):
    """Moderate community members and content"""

    def post(self, request, group_id):
        """Add/remove members, moderators, or ban users"""
        action = request.data.get('action')
        target_user_id = request.data.get('user_id')

        if not action or not target_user_id:
            return Response({'error': 'Action and user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id
        print(f"🔍 Moderation Debug - user_id: {user_id}, group_id: {group_id}")
        print(f"🔍 Group creator: {group.creator_id}, moderators: {group.moderators}")
        print(f"🔍 Can moderate: {group.can_moderate(user_id)}")

        try:
            if action == 'add_member':
                group.add_member(target_user_id, target_user_id, user_id)
                message = f'Added {target_user_id} as member'
            elif action == 'remove_member':
                group.remove_member(target_user_id, user_id)
                message = f'Removed {target_user_id} as member'
            elif action == 'add_moderator':
                group.add_moderator(target_user_id, target_user_id, user_id)
                message = f'Added {target_user_id} as moderator'
            elif action == 'remove_moderator':
                group.remove_moderator(target_user_id, user_id)
                message = f'Removed {target_user_id} as moderator'
            elif action == 'ban':
                group.ban_user(target_user_id, target_user_id, user_id)
                message = f'Banned {target_user_id}'
            elif action == 'unban':
                group.unban_user(target_user_id, user_id)
                message = f'Unbanned {target_user_id}'
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': request.user_id})
            return Response({
                'message': message,
                'group': serializer.data
            })

        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupAdminView(APIView):
    """Moderator-only community management"""

    def post(self, request, group_id):
        """Add/remove moderators (only existing moderators can do this)"""
        action = request.data.get('action')
        target_user_id = request.data.get('user_id')

        if not action or not target_user_id:
            return Response({'error': 'Action and user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        try:
            if action == 'add_moderator':
                group.add_moderator(target_user_id, target_user_id, user_id)
                message = f'Added {target_user_id} as moderator'
            elif action == 'remove_moderator':
                group.remove_moderator(target_user_id, user_id)
                message = f'Removed {target_user_id} as moderator'
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': request.user_id})
            return Response({
                'message': message,
                'group': serializer.data
            })

        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupSettingsView(APIView):
    """Update community settings"""

    def put(self, request, group_id):
        """Update group settings (only moderators can do this)"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        if user_id not in group.moderators and user_id != group.creator_id:
            return Response({'error': 'Only moderators can update group settings'}, status=status.HTTP_403_FORBIDDEN)

        allowed_fields = ['name', 'description', 'is_private']
        for field in allowed_fields:
            if field in request.data:
                setattr(group, field, request.data[field])

        if 'logo' in request.FILES:
            group.logo = request.FILES['logo']
        if 'banner' in request.FILES:
            group.banner = request.FILES['banner']

        group.save()

        serializer = UnifiedGroupSerializer(group, context={'request': request, 'user_id': request.user_id})
        return Response(serializer.data)


class GroupRulesView(APIView):
    """Manage community rules/guidelines"""

    def get(self, request, group_id):
        """Get all community rules"""
        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'group_id': group_id,
            'group_name': group.name,
            'rules': group.get_rules()
        })

    def post(self, request, group_id):
        """Add a new rule to the community (only moderators can do this)"""
        rule = request.data.get('rule')
        if not rule:
            return Response({'error': 'Rule content is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.add_rule(rule, request.user_id)
            return Response({
                'message': 'Rule added successfully',
                'rules': group.get_rules()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, group_id):
        """Update all community rules (only moderators can do this)"""
        rules = request.data.get('rules')
        if not isinstance(rules, list):
            return Response({'error': 'Rules must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.update_rules(rules, request.user_id)
            return Response({
                'message': 'Rules updated successfully',
                'rules': group.get_rules()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, group_id):
        """Remove a specific rule from the community (only moderators can do this)"""
        rule = request.data.get('rule')
        if not rule:
            return Response({'error': 'Rule content is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.remove_rule(rule, request.user_id)
            return Response({
                'message': 'Rule removed successfully',
                'rules': group.get_rules()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupMembersPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 50


class GroupMembersView(APIView):
    """List all members in a community with pagination"""

    def get(self, request, group_id):
        """Get paginated list of members in the community"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        # Get members data
        members = group.members if isinstance(group.members, list) else []
        member_names = group.member_names if isinstance(group.member_names, list) else []

        # Create member objects
        member_list = []
        for user_id, user_name in zip(members, member_names):
            member_list.append({
                'user_id': user_id,
                'user_name': user_name,
                'role': 'member'
            })

        # Paginate the results
        paginator = GroupMembersPagination()
        paginated_members = paginator.paginate_queryset(member_list, request)

        return paginator.get_paginated_response({
            'count': len(member_list),
            'members': paginated_members
        })


class GroupModeratorsView(APIView):
    """List all moderators in a community with pagination"""

    def get(self, request, group_id):
        """Get paginated list of moderators in the community"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        # Get moderators data
        moderators = group.moderators if isinstance(group.moderators, list) else []
        moderator_names = group.moderator_names if isinstance(group.moderator_names, list) else []

        # Create moderator objects
        moderator_list = []
        for user_id, user_name in zip(moderators, moderator_names):
            moderator_list.append({
                'user_id': user_id,
                'user_name': user_name,
                'role': 'moderator'
            })

        # Paginate the results
        paginator = GroupMembersPagination()
        paginated_moderators = paginator.paginate_queryset(moderator_list, request)

        return paginator.get_paginated_response({
            'count': len(moderator_list),
            'moderators': paginated_moderators
        })


class GroupBannedUsersView(APIView):
    """List all banned users in a community with pagination"""

    def get(self, request, group_id):
        """Get paginated list of banned users in the community"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        # Get banned users data
        banned_users = group.banned_users if isinstance(group.banned_users, list) else []
        banned_user_names = group.banned_user_names if isinstance(group.banned_user_names, list) else []

        # Create banned user objects
        banned_list = []
        for user_id, user_name in zip(banned_users, banned_user_names):
            banned_list.append({
                'user_id': user_id,
                'user_name': user_name,
                'role': 'banned'
            })

        # Paginate the results
        paginator = GroupMembersPagination()
        paginated_banned = paginator.paginate_queryset(banned_list, request)

        return paginator.get_paginated_response({
            'count': len(banned_list),
            'banned_users': paginated_banned
        })


class GroupDeleteView(APIView):
    """Delete a community (only moderators can do this)"""

    def delete(self, request, group_id):
        """Delete the group (only creator can do this)"""
        user_id = request.GET.get('user_id')

        if not user_id:
            return Response({
                'error': 'user_id query parameter is required',
                'example': 'DELETE /groups/{group_id}/?user_id=default_user_123'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if user_id != group.creator_id:
            return Response({'error': 'Only the group creator can delete this group'}, status=status.HTTP_403_FORBIDDEN)

        group_name = group.name
        group_id_value = group.id

        group.delete()

        return Response({
            'message': f'Group "{group_name}" has been successfully deleted',
            'deleted_group_id': group_id_value
        }, status=status.HTTP_200_OK)





class InviteLinkCreateView(APIView):
    """Create invite links for a community (moderators only)"""

    def post(self, request, group_id):
        """Create a new invite link"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(id=group_id)  # type: ignore
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        if user_id not in group.moderators and user_id != group.creator_id:
            return Response({'error': 'Only moderators can create invite links'}, status=status.HTTP_403_FORBIDDEN)

        expiration_hours = request.data.get('expiration_hours', 72)
        if expiration_hours not in [72, 168]:
            return Response({'error': 'Invalid expiration time. Choose 72 (hours) or 168 (1 week)'}, status=status.HTTP_400_BAD_REQUEST)

        invite_data = {
            'group': group.id,
            'created_by': user_id,
            'created_by_name': getattr(request, 'user_name', f"User {user_id}"),
            'expiration_hours': expiration_hours
        }

        serializer = InviteLinkSerializer(data=invite_data)
        if serializer.is_valid():
            invite_link = serializer.save()

            invite_url = f"https://qachirp.opencrafts.io/groups/{group_id}/join/invite/{invite_link.token}/"  # type: ignore

            return Response({
                'message': 'Invite link created successfully',
                'invite_link': InviteLinkSerializer(invite_link).data,
                'invite_url': invite_url
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InviteLinkJoinView(APIView):
    """Join a community using an invite link"""

    def post(self, request, group_id, invite_token):
        """Join group using invite link"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            invite_link = InviteLink._default_manager.get(token=invite_token, group=group)
        except InviteLink.DoesNotExist:  # type: ignore
            return Response({'error': 'Invalid invite link'}, status=status.HTTP_404_NOT_FOUND)

        if not invite_link.can_be_used():
            if invite_link.is_used:
                return Response({'error': 'This invite link has already been used. Kindly request for a new invite link from the community moderator.'}, status=status.HTTP_400_BAD_REQUEST)
            elif invite_link.is_expired():
                return Response({'error': 'This invite link has expired. Kindly request for a new invite link from the community moderator.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'This invite link cannot be used. Kindly request for a new invite link from the community moderator.'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = request.user_id
        user_name = request.data.get('user_name', getattr(request, 'user_name', f"User {user_id}"))
        user_email = request.data.get('user_email')

        if group.is_member(user_id):
            return Response({'message': 'Already a member of this community'}, status=status.HTTP_400_BAD_REQUEST)

        if user_id in group.banned_users:
            return Response({'error': 'You are banned from this community'}, status=status.HTTP_403_FORBIDDEN)

        try:
            group.add_member(user_id, user_name, user_id)

            invite_link.mark_as_used(user_id, user_name)

            return Response({
                'message': 'Successfully joined community using invite link',
                'group': UnifiedGroupSerializer(group, context={'request': request, 'user_id': request.user_id}).data
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InviteLinkListView(APIView):
    """List all invite links for a community (moderators only)"""

    def get(self, request, group_id):
        """Get all invite links for the community"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:  # type: ignore
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        if user_id not in group.moderators and user_id != group.creator_id:
            return Response({'error': 'Only moderators can view invite links'}, status=status.HTTP_403_FORBIDDEN)

        invite_links = InviteLink._default_manager.filter(group=group).order_by('-created_at')
        serializer = InviteLinkSerializer(invite_links, many=True)

        return Response({
            'group_name': group.name,
            'invite_links': serializer.data
        })

