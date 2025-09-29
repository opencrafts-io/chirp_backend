from rest_framework import serializers
from django.conf import settings

from users.models import User
from users.serializers import UserSerializer
from .models import Community, CommunityInvite, CommunityMembership, InviteLink


class UnifiedCommunitySerializer(serializers.ModelSerializer):
    creator_id = serializers.CharField(max_length=100)
    creator_name = serializers.CharField(max_length=100)
    is_private = serializers.BooleanField(default=False)
    moderators = serializers.ListField(child=serializers.CharField(), read_only=True)
    moderator_names = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    members = serializers.ListField(child=serializers.CharField(), read_only=True)
    member_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_users = serializers.ListField(child=serializers.CharField(), read_only=True)
    banned_user_names = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    rules = serializers.ListField(child=serializers.CharField(), read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    is_banned = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    can_moderate = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            "id",
            "name",
            "description",
            "creator_id",
            "creator_name",
            "moderators",
            "moderator_names",
            "members",
            "member_names",
            "banned_users",
            "banned_user_names",
            "is_private",
            "rules",
            "logo_url",
            "banner_url",
            "created_at",
            "updated_at",
            "is_banned",
            "can_post",
            "can_moderate",
            "member_count",
        ]
        read_only_fields = [
            "id",
            "moderators",
            "moderator_names",
            "members",
            "member_names",
            "banned_users",
            "banned_user_names",
            "rules",
            "created_at",
            "updated_at",
        ]

    def get_logo_url(self, obj):
        logo = obj.get_logo()
        if logo:
            request = self.context.get("request")
            if request:
                url = request.build_absolute_uri(logo.get_file_url())
                if getattr(settings, "USE_TLS", False):
                    url = url.replace("http://", "https://")

                if "qachirp.opencrafts.io" in url and "/qa-chirp/" not in url:
                    url = url.replace("/media/", "/qa-chirp/media/")

                return url
            return logo.get_file_url()
        return None

    def get_banner_url(self, obj):
        banner = obj.get_banner()
        if banner:
            request = self.context.get("request")
            if request:
                url = request.build_absolute_uri(banner.get_file_url())
                if getattr(settings, "USE_TLS", False):
                    url = url.replace("http://", "https://")

                if "qachirp.opencrafts.io" in url and "/qa-chirp/" not in url:
                    url = url.replace("/media/", "/qa-chirp/media/")

                return url
            return banner.get_file_url()
        return None

    def get_is_banned(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return False

        try:
            from users.models import User

            user = User.objects.get(user_id=user_id)
            return obj.group_memberships.filter(user=user, banned=True).exists()
        except:
            return False

    def get_can_post(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return None
        return obj.can_post(user_id)

    def get_can_moderate(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return None
        return obj.can_moderate(user_id)

    def get_creator_id(self, obj):
        return str(obj.creator.user_id) if obj.creator else None

    def get_creator_name(self, obj):
        return obj.creator.name if obj.creator else None

    def get_is_private(self, obj):
        return obj.private

    def get_moderators(self, obj):
        try:
            return [
                str(m.user.user_id)
                for m in obj.group_memberships.filter(role__in=["moderator", "creator"])
            ]
        except:
            return []

    def get_moderator_names(self, obj):
        try:
            return [
                m.user.name
                for m in obj.group_memberships.filter(role__in=["moderator", "creator"])
            ]
        except:
            return []

    def get_members(self, obj):
        try:
            return [
                str(m.user.user_id) for m in obj.group_memberships.filter(role="member")
            ]
        except:
            return []

    def get_member_names(self, obj):
        try:
            return [m.user.name for m in obj.group_memberships.filter(role="member")]
        except:
            return []

    def get_banned_users(self, obj):
        try:
            return [
                str(m.user.user_id) for m in obj.group_memberships.filter(banned=True)
            ]
        except:
            return []

    def get_banned_user_names(self, obj):
        try:
            return [m.user.name for m in obj.group_memberships.filter(banned=True)]
        except:
            return []

    def get_rules(self, obj):
        return obj.guidelines if isinstance(obj.guidelines, list) else []

    def get_member_count(self, obj):
        try:
            return obj.group_memberships.count()
        except:
            return 0

    def to_representation(self, instance):
        data = super().to_representation(instance)

        for field in [
            "moderators",
            "moderator_names",
            "members",
            "member_names",
            "banned_users",
            "banned_user_names",
        ]:
            if field in data and isinstance(data[field], list):
                data[field] = data[field][:5]

        return data


class CommunitySerializer(serializers.ModelSerializer):
    creator_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    creator = UserSerializer(read_only=True)
    banner_url = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            "id",
            "creator_id",
            "creator",
            "name",
            "description",
            "creator",
            "visibility",
            "private",
            "nsfw",
            "verified",
            "guidelines",
            "member_count",
            "moderator_count",
            "banned_users_count",
            "monthly_visitor_count",
            "weekly_visitor_count",
            "banner",
            "banner_url",
            "banner_width",
            "banner_height",
            "profile_picture",
            "profile_picture_url",
            "profile_picture_width",
            "profile_picture_height",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "member_count",
            "moderator_count",
            "banned_users_count",
            "monthly_visitor_count",
            "weekly_visitor_count",
            "banner_width",
            "banner_height",
            "profile_picture_width",
            "profile_picture_height",
            "created_at",
            "updated_at",
        ]

    def get_banner_url(self, obj):
        if obj.banner:
            try:
                return obj.banner.url
            except Exception:
                return None
        return None

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            try:
                return obj.profile_picture.url
            except Exception:
                return None
        return None


class CommunityInviteSerializer(serializers.ModelSerializer):
    inviter_id = serializers.CharField(read_only=True, max_length=100)

    class Meta:
        model = CommunityInvite
        fields = ["id", "community", "inviter_id", "invitee_id", "created_at"]
        read_only_fields = ["id", "inviter_id", "created_at"]

    def validate_invitee_id(self, value):
        """Validate invitee_id"""
        if not value or not value.strip():
            raise serializers.ValidationError("Invitee ID cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError(
                "Invitee ID cannot exceed 100 characters."
            )

        return value


class InviteLinkSerializer(serializers.ModelSerializer):
    """Serializer for community invite links"""

    community_name = serializers.CharField(source="community.name", read_only=True)
    created_by_name = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    can_be_used = serializers.BooleanField(read_only=True)

    class Meta:
        model = InviteLink
        fields = [
            "id",
            "community",
            "community_name",
            "created_by",
            "created_by_name",
            "token",
            "expiration_hours",
            "created_at",
            "expires_at",
            "is_used",
            "used_by",
            "used_by_name",
            "used_at",
            "is_expired",
            "can_be_used",
        ]
        read_only_fields = [
            "id",
            "community_name",
            "created_by",
            "created_by_name",
            "token",
            "created_at",
            "expires_at",
            "is_used",
            "used_by",
            "used_by_name",
            "used_at",
            "is_expired",
            "can_be_used",
        ]

    def create(self, validated_data):
        """Create invite link with auto-generated token"""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(32))
        while InviteLink._default_manager.filter(token=token).exists():
            token = "".join(secrets.choice(alphabet) for _ in range(32))

        validated_data["token"] = token
        return super().create(validated_data)


class CommunityMembershipSerializer(serializers.ModelSerializer):
    community = CommunitySerializer(read_only=True)
    user = UserSerializer(read_only=True)
    banned_by = UserSerializer(read_only=True)

    community_id = serializers.PrimaryKeyRelatedField(
        queryset=Community.objects.all(),
        source="community",
        write_only=True,
        required=False,
        allow_null=True,
    )
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        write_only=True,
        required=False,
        allow_null=True,
    )
    banned_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="banned_by",
        write_only=True,
        required=False,
        allow_null=True,
    )
    role = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = CommunityMembership
        fields = [
            "id",
            "community",
            "community_id",
            "user",
            "user_id",
            "role",
            "banned",
            "banned_by_id",
            "banned_by",
            "banning_reason",
            "banned_at",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "joined_at",
            "banned_at",
            "banned_by",
        ]
