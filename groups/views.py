from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Group, GroupInvite
from .serializers import GroupSerializer
from chirp.permissions import require_community_role, CommunityPermission
from django.shortcuts import get_object_or_404
from django.db import models
from django.core.exceptions import ValidationError


class GroupListView(APIView):
    """List all public groups or groups user is a member of"""

    def get(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = request.user_id

        # Get public groups
        public_groups = Group.objects.filter(is_private=False)

        # Get private groups user is a member of
        user_groups = Group.objects.filter(
            models.Q(members__contains=[user_id]) |
            models.Q(moderators__contains=[user_id]) |
            models.Q(admins__contains=[user_id]) |
            models.Q(creator_id=user_id)
        )

        # Combine and remove duplicates
        all_groups = list(public_groups) + list(user_groups)
        unique_groups = list({group.id: group for group in all_groups}.values())

        serializer = GroupSerializer(unique_groups, many=True)
        return Response(serializer.data)


class GroupCreateView(APIView):
    """Create a new community"""

    def post(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        data['creator_id'] = request.user_id

        # Creator automatically becomes admin and member
        data['admins'] = [request.user_id]
        data['members'] = [request.user_id]

        serializer = GroupSerializer(data=data)
        if serializer.is_valid():
            group = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupDetailView(APIView):
    """View community details"""

    def get(self, request, group_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user can view this group
        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = GroupSerializer(group)
        return Response(serializer.data)


class GroupJoinView(APIView):
    """Join a community"""

    def post(self, request, group_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        # Check if user is already a member
        if group.is_member(user_id):
            return Response({'message': 'Already a member'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user is banned
        if user_id in group.banned_users:
            return Response({'error': 'You are banned from this community'}, status=status.HTTP_403_FORBIDDEN)

        # Add user as member
        group.add_member(user_id, user_id)  # Self-join for public groups

        serializer = GroupSerializer(group)
        return Response(serializer.data)


class GroupLeaveView(APIView):
    """Leave a community"""

    def post(self, request, group_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        # Creator cannot leave
        if user_id == group.creator_id:
            return Response({'error': 'Creator cannot leave the community'}, status=status.HTTP_400_BAD_REQUEST)

        # Remove user from all roles
        if user_id in group.admins:
            current_admins = list(group.admins)
            current_admins.remove(user_id)
            group.admins = current_admins

        if user_id in group.moderators:
            current_moderators = list(group.moderators)
            current_moderators.remove(user_id)
            group.moderators = current_moderators

        if user_id in group.members:
            current_members = list(group.members)
            current_members.remove(user_id)
            group.members = current_members

        group.save()

        return Response({'message': 'Successfully left the community'})


class GroupModerationView(APIView):
    """Moderate community members and content"""

    @require_community_role('moderator')
    def post(self, request, group_id):
        """Add/remove members, moderators, or ban users"""
        action = request.data.get('action')
        target_user_id = request.data.get('user_id')

        if not action or not target_user_id:
            return Response({'error': 'Action and user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        try:
            if action == 'add_member':
                group.add_member(target_user_id, user_id)
                message = f'Added {target_user_id} as member'
            elif action == 'remove_member':
                group.remove_member(target_user_id, user_id)
                message = f'Removed {target_user_id} as member'
            elif action == 'add_moderator':
                group.add_moderator(target_user_id, user_id)
                message = f'Added {target_user_id} as moderator'
            elif action == 'remove_moderator':
                group.remove_moderator(target_user_id, user_id)
                message = f'Removed {target_user_id} as moderator'
            elif action == 'ban':
                group.ban_user(target_user_id, user_id)
                message = f'Banned {target_user_id}'
            elif action == 'unban':
                group.unban_user(target_user_id, user_id)
                message = f'Unbanned {target_user_id}'
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = GroupSerializer(group)
            return Response({
                'message': message,
                'group': serializer.data
            })

        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupAdminView(APIView):
    """Admin-only community management"""

    @require_community_role('admin')
    def post(self, request, group_id):
        """Add/remove admins (only existing admins can do this)"""
        action = request.data.get('action')
        target_user_id = request.data.get('user_id')

        if not action or not target_user_id:
            return Response({'error': 'Action and user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        try:
            if action == 'add_admin':
                group.add_admin(target_user_id, user_id)
                message = f'Added {target_user_id} as admin'
            elif action == 'remove_admin':
                group.remove_admin(target_user_id, user_id)
                message = f'Removed {target_user_id} as admin'
            else:
                return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = GroupSerializer(group)
            return Response({
                'message': message,
                'group': serializer.data
            })

        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GroupSettingsView(APIView):
    """Update community settings"""

    @require_community_role('admin')
    def put(self, request, group_id):
        """Update group settings (only admins can do this)"""
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only allow updating certain fields
        allowed_fields = ['name', 'description', 'is_private']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = GroupSerializer(group, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupRulesView(APIView):
    """Manage community rules/guidelines"""

    def get(self, request, group_id):
        """Get community rules (anyone can view if they can access the group)"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user can view this group
        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'group_id': group_id,
            'group_name': group.name,
            'rules': group.get_rules()
        })

    @require_community_role('admin')
    def post(self, request, group_id):
        """Add a new rule to the community (only admins can do this)"""
        rule = request.data.get('rule')
        if not rule:
            return Response({'error': 'Rule content is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.add_rule(rule, request.user_id)
            return Response({
                'message': 'Rule added successfully',
                'rules': group.get_rules()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @require_community_role('admin')
    def put(self, request, group_id):
        """Update all community rules (only admins can do this)"""
        rules = request.data.get('rules')
        if not isinstance(rules, list):
            return Response({'error': 'Rules must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.update_rules(rules, request.user_id)
            return Response({
                'message': 'Rules updated successfully',
                'rules': group.get_rules()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @require_community_role('admin')
    def delete(self, request, group_id):
        """Remove a specific rule from the community (only admins can do this)"""
        rule = request.data.get('rule')
        if not rule:
            return Response({'error': 'Rule content is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            group.remove_rule(rule, request.user_id)
            return Response({
                'message': 'Rule removed successfully',
                'rules': group.get_rules()
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

