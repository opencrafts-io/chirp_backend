from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Group, GroupInvite, GroupPost
from .serializers import GroupSerializer, GroupPostSerializer, GroupInviteSerializer

class GroupListCreateView(APIView):
    def get(self, request):
        # Require authentication for viewing groups
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        # The filter works when we use the user_id as a string in the contains lookup
        user_groups = Group.objects.filter(members__contains=request.user_id).order_by('-created_at')

        # Apply pagination
        paginator = StandardResultsSetPagination()
        paginated_groups = paginator.paginate_queryset(user_groups, request)

        serializer = GroupSerializer(paginated_groups, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Require authentication for creating groups
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        serializer = GroupSerializer(data=data)
        if serializer.is_valid():
            serializer.save(
                creator_id=request.user_id,
                admins=[request.user_id],
                members=[request.user_id]
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

class GroupDiscoverView(APIView):
    def get(self, request):
        # Require authentication for viewing groups
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        # Get all groups and add membership status for the current user
        all_groups = Group.objects.all().order_by('-created_at')

        # Apply pagination
        paginator = StandardResultsSetPagination()
        paginated_groups = paginator.paginate_queryset(all_groups, request)

        # Add membership status to each group
        groups_with_status = []
        for group in paginated_groups:
            group_data = GroupSerializer(group).data
            group_data['is_member'] = request.user_id in group.members
            group_data['is_admin'] = request.user_id in group.admins
            group_data['is_creator'] = request.user_id == group.creator_id
            groups_with_status.append(group_data)

        return paginator.get_paginated_response(groups_with_status)

class GroupJoinView(APIView):
    def post(self, request, group_name):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(name=group_name)

            # Check if user is already a member
            if request.user_id in group.members:
                return Response({
                    'message': 'Already a member of this group',
                    'group': GroupSerializer(group).data
                }, status=status.HTTP_200_OK)

            # Add user to group members
            group.members.append(request.user_id)
            group.save()

            return Response({
                'message': f'Successfully joined group "{group.name}"',
                'group': GroupSerializer(group).data
            }, status=status.HTTP_200_OK)

        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

class GroupLeaveView(APIView):
    def post(self, request, group_name):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(name=group_name)

            # Check if user is a member
            if request.user_id not in group.members:
                return Response({'error': 'Not a member of this group'}, status=status.HTTP_400_BAD_REQUEST)

            # Prevent creator from leaving (they should transfer ownership or delete the group)
            if request.user_id == group.creator_id:
                return Response({'error': 'Group creator cannot leave. Transfer ownership or delete the group.'}, status=status.HTTP_400_BAD_REQUEST)

            # Remove user from group members
            group.members.remove(request.user_id)

            # Remove from admins if they were an admin
            if request.user_id in group.admins:
                group.admins.remove(request.user_id)

            group.save()

            return Response({
                'message': f'Successfully left group "{group.name}"',
                'group': GroupSerializer(group).data
            }, status=status.HTTP_200_OK)

        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

class GroupAddMemberView(APIView):
    def post(self, request, group_name):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(name=group_name)
            if request.user_id not in group.admins:
                return Response({'error': 'Not an admin'}, status=status.HTTP_403_FORBIDDEN)
            user_id = request.data.get('user_id')
            if user_id and user_id not in group.members:
                group.members.append(user_id)
                group.save()
                # Send notification to group about new member
                notification = f"User {user_id} has been added to the group."
                # TO DO!!!!! NOTIFICATION SYSTEM LINKING
                return Response({
                    **GroupSerializer(group).data,
                    'notification': notification
                })
            return Response(GroupSerializer(group).data)
        except Group.DoesNotExist:
            return Response({'error': 'Group Not Found'}, status=status.HTTP_404_NOT_FOUND)


class GroupInviteView(APIView):
    def post(self, request, group_name):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(name=group_name)
            if request.user_id not in group.admins:
                return Response({'error': 'Not an admin'}, status=status.HTTP_403_FORBIDDEN)
            data = request.data.copy()
            data['group'] = group.id
            serializer = GroupInviteSerializer(data=data)
            if serializer.is_valid():
                serializer.save(inviter_id=request.user_id)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)


class GroupAcceptInviteView(APIView):
    def post(self, request, invite_id):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            invite = GroupInvite.objects.get(id=invite_id, invitee_id=request.user_id)
            group = invite.group
            if request.user_id not in group.members:
                group.members.append(request.user_id)
                group.save()
            invite.delete()  # Always delete the invite
            return Response(GroupSerializer(group).data)
        except GroupInvite.DoesNotExist:
            return Response({'error': 'Invite not Found'}, status=status.HTTP_404_NOT_FOUND)

class GroupPostListCreateView(APIView):
    def get(self, request, group_name):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        try:
            group = Group.objects.get(name=group_name)
            if request.user_id not in group.members:
                return Response({'error': 'Not a group member'}, status=status.HTTP_403_FORBIDDEN)

            posts = GroupPost.objects.filter(group=group).order_by("-created_at")

            # Apply pagination
            paginator = StandardResultsSetPagination()
            paginated_posts = paginator.paginate_queryset(posts, request)

            serializer = GroupPostSerializer(paginated_posts, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, group_name):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            group = Group.objects.get(name=group_name)
            if request.user_id not in group.members:
                return Response({'error': 'Not a group member'}, status=status.HTTP_403_FORBIDDEN)
            data = request.data.copy()
            data['group'] = group.id
            serializer = GroupPostSerializer(data=data)
            if serializer.is_valid():
                serializer.save(user_id=request.user_id)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

