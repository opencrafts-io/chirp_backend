from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Group, GroupInvite, GroupPost
from .serializers import GroupSerializer, GroupPostSerializer, GroupPostSerializer, GroupInviteSerializer

class GroupListCreateView(APIView):
    def get(self, request):
        groups = Group.objects.filter(members__contains=[request.user_id])
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['creator_id'] = request.user_id
        data['admins'] = request.user_id
        data['members'] = request.user_id
        serializer = GroupSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

class GroupAddMemberView(APIView):
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            if request.user_id not in group.admins:
                return Response({'error': 'Not an admin'}, status=status.HTTP_403_FORBIDDEN)
            user_id = request.data.get('user_id')
            if user_id and user_id not in group.members:
                group.members.append(user_id)
                group.save()
            return Response(GroupSerializer(group).data)
        except Group.DoesNotExist:
            return Response({'error': 'Group Not Found'}, status=status.HTTP_404_NOT_FOUND)


class GroupInviteView(APIView):
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            if request.user_id not in group.admins:
                return Response({'error': 'Not an admin'}, status=status.HTTP_403_FORBIDDEN)
            data = request.data.copy()
            data['group'] = group_id
            data['inviter_id'] = request.user_id
            serializer = GroupInviteSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)


class GroupAcceptInviteView(APIView):
    def post(self, request, invite_id):
        try:
            invite = GroupInvite.objects.get(id=invite_id, invitee_id=request.user_id)
            group = invite.group
            if request.user_id not in group.members:
                group.members.append(request.user_id)
                group.save()
                invite.delete()
            return Response(GroupSerializer(group).data)
        except GroupInvite.DoesNotExist:
            return Response({'error': 'Invite not Found'}, status=status.HTTP_404_NOT_FOUND)

class GroupPostListCreateView(APIView):
    def get(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            if request.user_id not in group.members:
                return Response({'error': 'Not a group member'}, status=status.HTTP_403_FORBIDDEN)
            posts = GroupPost.objects.filter(group=group)
            serializer = GroupPostSerializer(posts, many=True)
            return Response(serializer.data)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id)
            if request.user_id not in group.members:
                return Response({'error': 'Not a group member'}, status=status.HTTP_403_FORBIDDEN)
            data = request.data.copy()
            data['user_id'] = request.user_id
            data['group'] = group_id
            serializer = GroupPostSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

