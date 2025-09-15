from rest_framework import serializers
from django.conf import settings
from .models import Group, GroupPost, GroupInvite, InviteLink, GroupImage


class GroupImageSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = GroupImage
        fields = ["id", "image_type", "file_url", "file_size_mb", "original_filename", "created_at"]

    def get_file_url(self, obj):
        """Generate the full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(obj.file.url)
                if getattr(settings, 'USE_TLS', False):
                    url = url.replace('http://', 'https://')
                return url
            return obj.file.url
        return None

    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return obj.get_file_size_mb()


class UnifiedGroupSerializer(serializers.ModelSerializer):
    creator_id = serializers.CharField(max_length=100)
    creator_name = serializers.CharField(max_length=100)
    is_private = serializers.BooleanField(default=False)
    moderators = serializers.ListField(child=serializers.CharField(), read_only=True)
    moderator_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    members = serializers.ListField(child=serializers.CharField(), read_only=True)
    member_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_users = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_user_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    rules = serializers.ListField(child=serializers.CharField(), read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    is_banned = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    can_moderate = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'creator_id', 'creator_name', 'moderators',
            'moderator_names', 'members', 'member_names', 'banned_users',
            'banned_user_names', 'is_private', 'rules', 'logo_url', 'banner_url',
            'created_at', 'updated_at', 'is_banned', 'can_post', 'can_moderate', 'member_count'
        ]
        read_only_fields = [
            'id', 'moderators', 'moderator_names', 'members', 'member_names',
            'banned_users', 'banned_user_names', 'rules', 'created_at', 'updated_at'
        ]

    def get_logo_url(self, obj):
        logo = obj.get_logo()
        if logo:
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(logo.get_file_url())
                if getattr(settings, 'USE_TLS', False):
                    url = url.replace('http://', 'https://')
                return url
            return logo.get_file_url()
        return None

    def get_banner_url(self, obj):
        banner = obj.get_banner()
        if banner:
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(banner.get_file_url())
                if getattr(settings, 'USE_TLS', False):
                    url = url.replace('http://', 'https://')
                return url
            return banner.get_file_url()
        return None

    def get_is_banned(self, obj):
        user_id = self.context.get('user_id')
        if not user_id:
            return False

        banned_users = obj.banned_users if isinstance(obj.banned_users, list) else []
        return user_id in banned_users

    def get_can_post(self, obj):
        user_id = self.context.get('user_id')
        if not user_id:
            return None
        return obj.can_post(user_id)

    def get_can_moderate(self, obj):
        user_id = self.context.get('user_id')
        if not user_id:
            return None
        return obj.can_moderate(user_id)

    def get_member_count(self, obj):
        try:
            return obj.memberships.count()
        except:
            all_user_ids = set()
            all_user_ids.add(obj.creator_id)
            moderators = obj.moderators if isinstance(obj.moderators, list) else []
            all_user_ids.update(moderators)
            members = obj.members if isinstance(obj.members, list) else []
            all_user_ids.update(members)
            return len(all_user_ids)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Limit lists to 5 items for consistency
        for field in ['moderators', 'moderator_names', 'members', 'member_names', 'banned_users', 'banned_user_names']:
            if field in data and isinstance(data[field], list):
                data[field] = data[field][:5]

        return data




class GroupSerializer(serializers.ModelSerializer):
    creator_id = serializers.CharField(max_length=100)
    creator_name = serializers.CharField(max_length=100)
    is_private = serializers.BooleanField(default=False)
    moderators = serializers.ListField(child=serializers.CharField(), required=False)
    moderator_names = serializers.ListField(child=serializers.CharField(), required=False)
    members = serializers.ListField(child=serializers.CharField(), required=False)
    member_names = serializers.ListField(child=serializers.CharField(), required=False)
    banned_users = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_user_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    rules = serializers.ListField(child=serializers.CharField(), read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()

    is_banned = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    can_moderate = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'creator_id', 'creator_name', 'moderators',
            'moderator_names', 'members', 'member_names', 'banned_users',
            'banned_user_names', 'is_private', 'rules', 'logo_url', 'banner_url',
            'created_at', 'updated_at', 'is_banned', 'can_post', 'can_moderate'
        ]
        read_only_fields = [
            'id', 'banned_users', 'banned_user_names', 'rules', 'created_at', 'updated_at'
        ]

    def validate_name(self, value):
        """Validate group name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Group name cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Group name cannot exceed 100 characters.")

        return value

    def get_is_banned(self, obj):
        """Check if user is banned from this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False

        banned_users = obj.banned_users if isinstance(obj.banned_users, list) else []
        return request.user_id in banned_users

    def get_can_post(self, obj):
        """Check if user can post in this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False
        return obj.can_post(request.user_id)

    def get_can_moderate(self, obj):
        """Check if user can moderate this group"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user_id'):
            return False
        return obj.can_moderate(request.user_id)

    def get_logo_url(self, obj):
        """Get the full URL for the logo"""
        logo = obj.get_logo()
        if logo:
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(logo.get_file_url())
                if getattr(settings, 'USE_TLS', False):
                    url = url.replace('http://', 'https://')
                return url
            return logo.get_file_url()
        return None

    def get_banner_url(self, obj):
        """Get the full URL for the banner"""
        banner = obj.get_banner()
        if banner:
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(banner.get_file_url())
                if getattr(settings, 'USE_TLS', False):
                    url = url.replace('http://', 'https://')
                return url
            return banner.get_file_url()
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


class InviteLinkSerializer(serializers.ModelSerializer):
    """Serializer for community invite links"""

    group_name = serializers.CharField(source='group.name', read_only=True)
    created_by_name = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    can_be_used = serializers.BooleanField(read_only=True)

    class Meta:
        model = InviteLink
        fields = [
            'id', 'group', 'group_name', 'created_by', 'created_by_name',
            'token', 'expiration_hours', 'created_at', 'expires_at',
            'is_used', 'used_by', 'used_by_name', 'used_at',
            'is_expired', 'can_be_used'
        ]
        read_only_fields = [
            'id', 'group_name', 'created_by', 'created_by_name',
            'token', 'created_at', 'expires_at', 'is_used',
            'used_by', 'used_by_name', 'used_at', 'is_expired', 'can_be_used'
        ]

    def create(self, validated_data):
        """Create invite link with auto-generated token"""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(32))
        while InviteLink._default_manager.filter(token=token).exists():
            token = ''.join(secrets.choice(alphabet) for _ in range(32))

        validated_data['token'] = token
        return super().create(validated_data)

