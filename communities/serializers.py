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
        """
        Builds the absolute URL for a community's logo if one exists.
        
        If the community has a logo, returns its URL; when a request is present in the serializer context the URL is built as an absolute URI, otherwise the raw file URL is returned. If settings.USE_TLS is True the scheme is changed to `https`. For the QA host `qachirp.opencrafts.io` the path is adjusted to include `/qa-chirp/` by replacing `/media/` with `/qa-chirp/media/` when needed.
        
        Parameters:
            obj: An object with a `get_logo()` method that returns a file-like object with `get_file_url()`.
        
        Returns:
            The logo URL as a string, or `None` if no logo is available.
        """
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
        """
        Return an absolute URL for the community's banner image, or None if no banner is available.
        
        Parameters:
        	obj: An object with a `get_banner()` method that returns a media-like object exposing `get_file_url()`.
        
        Returns:
        	banner_url (str): Absolute URL to the banner image with TLS and QA-host adjustments applied, or `None` if the object has no banner.
        """
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
        """
        Check whether the current context user is banned from the given community.
        
        Parameters:
            obj (Community): The community instance whose memberships will be checked. Uses `self.context["user_id"]` to identify the user; if `user_id` is missing, not found, or an error occurs, the function returns `False`.
        
        Returns:
            bool: `True` if the context user has a banned membership in the community, `False` otherwise.
        """
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
        """
        Determine whether the current context user is allowed to post in the provided community.
        
        Parameters:
            obj: The community object to check permissions against.
        
        Returns:
            `True` if the context user can post in the community, `False` if they cannot, or `None` if no user is present in the serializer context.
        """
        user_id = self.context.get("user_id")
        if not user_id:
            return None
        return obj.can_post(user_id)

    def get_can_moderate(self, obj):
        """
        Determine whether the user from the serializer context has moderation privileges for the given community.
        
        Parameters:
            obj: The community instance to check.
        
        Returns:
            `True` if the context user can moderate the community, `False` if they cannot, or `None` if no user is present in the serializer context.
        """
        user_id = self.context.get("user_id")
        if not user_id:
            return None
        return obj.can_moderate(user_id)

    def get_creator_id(self, obj):
        """
        Get the community creator's user ID or None if the community has no creator.
        
        Returns:
            str: The creator's `user_id` as a string if a creator exists, `None` otherwise.
        """
        return str(obj.creator.user_id) if obj.creator else None

    def get_creator_name(self, obj):
        """
        Return the creator's display name for the given community or None.
        
        Parameters:
            obj: Community instance whose creator name will be returned.
        
        Returns:
            The creator's name as a string, or `None` if no creator is set.
        """
        return obj.creator.name if obj.creator else None

    def get_is_private(self, obj):
        """
        Return whether the community is private.
        
        Returns:
            True if the community's `private` flag is set, False otherwise.
        """
        return obj.private

    def get_moderators(self, obj):
        """
        List moderator user IDs for the given community.
        
        Parameters:
            obj: Community instance to extract moderator and creator memberships from.
        
        Returns:
            List of moderator user IDs as strings (includes members with role "moderator" or "creator"); returns an empty list on error.
        """
        try:
            return [
                str(m.user.user_id)
                for m in obj.group_memberships.filter(role__in=["moderator", "creator"])
            ]
        except:
            return []

    def get_moderator_names(self, obj):
        """
        Return the display names of moderators (including the creator) for the given community.
        
        Parameters:
        	obj: Community
        		The community instance to retrieve moderator names from.
        
        Returns:
        	moderator_names (list[str]): A list of moderator display names; an empty list if there are no moderators or if an error occurs.
        """
        try:
            return [
                m.user.name
                for m in obj.group_memberships.filter(role__in=["moderator", "creator"])
            ]
        except:
            return []

    def get_members(self, obj):
        """
        List member user IDs for the community.
        
        Parameters:
            obj (Community): The community instance whose memberships will be queried.
        
        Returns:
            list[str]: A list of member `user_id` values as strings. Returns an empty list if memberships cannot be retrieved.
        """
        try:
            return [
                str(m.user.user_id) for m in obj.group_memberships.filter(role="member")
            ]
        except:
            return []

    def get_member_names(self, obj):
        """
        Return the display names of users who have the "member" role in the given community.
        
        Parameters:
            obj: Community: The community instance whose memberships will be inspected.
        
        Returns:
            list[str]: A list of member user names; returns an empty list if memberships cannot be accessed or an error occurs.
        """
        try:
            return [m.user.name for m in obj.group_memberships.filter(role="member")]
        except:
            return []

    def get_banned_users(self, obj):
        """
        Return the list of banned users' IDs for the given community.
        
        Parameters:
            obj: Community model instance whose group memberships will be inspected.
        
        Returns:
            list[str]: A list of banned users' `user_id` values as strings. Returns an empty list if the banned membership list cannot be retrieved.
        """
        try:
            return [
                str(m.user.user_id) for m in obj.group_memberships.filter(banned=True)
            ]
        except:
            return []

    def get_banned_user_names(self, obj):
        """
        Get the display names of users who are banned from the community.
        
        Parameters:
        	obj: The community instance whose group memberships will be inspected.
        
        Returns:
        	list[str]: A list of banned users' `name` values; returns an empty list if the information is unavailable or an error occurs.
        """
        try:
            return [m.user.name for m in obj.group_memberships.filter(banned=True)]
        except:
            return []

    def get_rules(self, obj):
        """
        Get the community's rules as a list.
        
        Parameters:
        	obj (Community): Community instance from which to read guidelines.
        
        Returns:
        	list: The community's guidelines if they are a list, otherwise an empty list.
        """
        return obj.guidelines if isinstance(obj.guidelines, list) else []

    def get_member_count(self, obj):
        """
        Return the number of group memberships associated with the given community.
        
        Parameters:
        	obj: The community instance whose group memberships will be counted.
        
        Returns:
        	member_count (int): The count of group memberships for `obj`. Returns 0 if the count cannot be determined.
        """
        try:
            return obj.group_memberships.count()
        except:
            return 0

    def to_representation(self, instance):
        """
        Limit specific list fields in the serialized representation to at most five items.
        
        After obtaining the standard representation from the superclass, truncates any present list in
        `moderators`, `moderator_names`, `members`, `member_names`, `banned_users`, and `banned_user_names`
        to the first five elements. Other fields are returned unchanged.
        
        Returns:
            dict: The serialized representation with the specified list fields truncated when present.
        """
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
        """
        Return the banner image URL for the given community or None if unavailable.
        
        Parameters:
            obj (Community): The community model instance to read the banner from.
        
        Returns:
            banner_url (str or None): The banner's URL string if the community has a banner and the URL can be accessed, otherwise `None`.
        """
        if obj.banner:
            try:
                return obj.banner.url
            except Exception:
                return None
        return None

    def get_profile_picture_url(self, obj):
        """
        Return the profile picture URL for the given community if available.
        
        Parameters:
            obj (Community): The community instance to read the profile picture from.
        
        Returns:
            profile_picture_url (str): The profile picture URL, or `None` if no picture is set or the URL cannot be resolved.
        """
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
        """
        Validate an invitee identifier against emptiness and length constraints.
        
        Parameters:
            value (str): The invitee ID to validate.
        
        Returns:
            str: The validated invitee ID.
        
        Raises:
            serializers.ValidationError: If `value` is empty (after trimming) or longer than 100 characters.
        """
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
        """
        Create an InviteLink and assign a unique 32-character alphanumeric token.
        
        The method injects a generated alphanumeric token into validated_data and ensures the token does not collide with existing InviteLink tokens before creating the instance.
        
        Parameters:
            validated_data (dict): Serializer-validated fields to use when creating the InviteLink.
        
        Returns:
            InviteLink: The newly created InviteLink instance with a unique `token` field.
        """
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
