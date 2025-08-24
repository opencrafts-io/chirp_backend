from rest_framework import serializers
from .models import Group, GroupPost, GroupInvite


class GroupSerializer(serializers.ModelSerializer):
    creator_id = serializers.CharField(read_only=True, max_length=100)
    creator_name = serializers.CharField(read_only=True, max_length=100)
    is_private = serializers.BooleanField(default=False)
    moderators = serializers.ListField(child=serializers.CharField(), read_only=True)
    moderator_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_users = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_user_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    rules = serializers.ListField(child=serializers.CharField(), read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    # Image fields
    logo = serializers.ImageField(required=False, allow_null=True)
    banner = serializers.ImageField(required=False, allow_null=True)
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()

    user_role = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    can_moderate = serializers.SerializerMethodField()
    can_admin = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'creator_id', 'creator_name', 'admins', 'admin_names',
            'moderators', 'moderator_names', 'members', 'member_names', 'banned_users',
            'banned_user_names', 'is_private', 'rules', 'logo', 'banner', 'logo_url', 'banner_url',
            'created_at', 'updated_at', 'user_role', 'can_post', 'can_moderate', 'can_admin'
        ]
        read_only_fields = [
            'id', 'creator_id', 'creator_name', 'admins', 'admin_names', 'moderators',
            'moderator_names', 'members', 'member_names', 'banned_users',
            'banned_user_names', 'rules', 'created_at', 'updated_at'
        ]

    def validate_name(self, value):
        """Validate group name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Group name cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Group name cannot exceed 100 characters.")

        return value

    def get_user_role(self, obj):
        """Get the current user's role in this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return None

        user_id = request.user_id
        if obj.creator_id == user_id:
            return 'creator'
        elif user_id in obj.admins:
            return 'admin'
        elif user_id in obj.moderators:
            return 'moderator'
        elif user_id in obj.members:
            return 'member'
        elif user_id in obj.banned_users:
            return 'banned'
        else:
            return 'none'

    def get_can_post(self, obj):
        """Check if current user can post in this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False

        return obj.can_post(request.user_id)

    def get_can_moderate(self, obj):
        """Check if current user can moderate this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False

        return obj.is_moderator(request.user_id)

    def get_can_admin(self, obj):
        """Check if current user can admin this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False

        return obj.is_admin(request.user_id)

    def get_logo_url(self, obj):
        """Get the full URL for the logo"""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    def get_banner_url(self, obj):
        """Get the full URL for the banner"""
        if obj.banner:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None


class GroupPostSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(read_only=True, max_length=100)

    class Meta:
        model = GroupPost
        fields = ['id', 'group', 'user_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']

    def validate_content(self, value):
        """Validate group post content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")

        return value


class GroupInviteSerializer(serializers.ModelSerializer):
    inviter_id = serializers.CharField(read_only=True, max_length=100)

    class Meta:
        model = GroupInvite
        fields = ['id', 'group', 'inviter_id', 'invitee_id', 'created_at']
        read_only_fields = ['id', 'inviter_id', 'created_at']

    def validate_invitee_id(self, value):
        """Validate invitee_id"""
        if not value or not value.strip():
            raise serializers.ValidationError("Invitee ID cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Invitee ID cannot exceed 100 characters.")

        return value

