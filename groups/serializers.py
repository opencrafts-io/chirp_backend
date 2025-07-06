from rest_framework import serializers
from .models import Group, GroupPost, GroupInvite

class GroupSerializer(serializers.ModelSerializer):
    creator_id = serializers.CharField(required=False, max_length=100)

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'creator_id', 'admins', 'members', 'created_at']
        read_only_fields =  ['id', 'created_at']

    def validate_name(self, value):
        """Validate group name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Group name cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Group name cannot exceed 100 characters.")

        return value

class GroupPostSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=False, max_length=100)

    class Meta:
        model = GroupPost
        fields = ['id', 'group', 'user_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_content(self, value):
        """Validate group post content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")

        return value

class GroupInviteSerializer(serializers.ModelSerializer):
    inviter_id = serializers.CharField(required=False, max_length=100)

    class Meta:
        model = GroupInvite
        fields = ['id', 'group', 'inviter_id', 'invitee_id', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_invitee_id(self, value):
        """Validate invitee_id"""
        if not value or not value.strip():
            raise serializers.ValidationError("Invitee ID cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Invitee ID cannot exceed 100 characters.")

        return value

