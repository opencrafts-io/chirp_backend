from rest_framework import serializers
from .models import Group, GroupPost, GroupInvite

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'creator_id', 'admins', 'members', 'created_at']
        read_only_fields =  ['id', 'creator_id', 'admins', 'members', 'created_at']

class GroupPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPost
        fields = ['id', 'group', 'user_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']

class GroupInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupInvite
        fields = ['id', 'group', 'invitee_id', 'inviter_id', 'created_at']
        read_only_fields = ['id', 'inviter_id', 'created_at']

