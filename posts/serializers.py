from rest_framework import serializers
from django.conf import settings
from .models import Attachment, Post, Comment
from users.models import User


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "attachment_type", "file_url", "file_size_mb", "original_filename", "created_at"]

    def get_file_url(self, obj):
        """Generate the full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                url = request.build_absolute_uri(obj.file.url)
                if getattr(settings, 'USE_TLS', False):
                    url = url.replace('http://', 'https://')

                if 'qachirp.opencrafts.io' in url and '/qa-chirp/' not in url:
                    url = url.replace('/media/', '/qa-chirp/media/')

                return url
            return obj.file.url
        return None

    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return obj.get_file_size_mb()


class GroupSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()


class UserSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    vibe_points = serializers.SerializerMethodField()

    def get_id(self, obj):
        if hasattr(obj, 'user_ref') and obj.user_ref:
            return obj.user_ref.user_id
        return getattr(obj, 'user_id', 'unknown')

    def get_name(self, obj):
        if hasattr(obj, 'user_ref') and obj.user_ref:
            return obj.user_ref.user_name
        return getattr(obj, 'user_name', 'Unknown User')

    def get_email(self, obj):
        if hasattr(obj, 'user_ref') and obj.user_ref:
            return obj.user_ref.email
        return getattr(obj, 'email', None)

    def get_avatar_url(self, obj):
        if hasattr(obj, 'user_ref') and obj.user_ref:
            return obj.user_ref.avatar_url
        return getattr(obj, 'avatar_url', None)

    def get_username(self, obj):
        if hasattr(obj, 'user_ref') and obj.user_ref:
            return obj.user_ref.username
        return None

    def get_vibe_points(self, obj):
        if hasattr(obj, 'user_ref') and obj.user_ref:
            return obj.user_ref.vibe_points or 0
        return 0


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'content', 'user_id', 'user_name', 'user_avatar',
                 'created_at', 'updated_at', 'depth', 'like_count', 'is_liked', 'replies']

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True, context=self.context).data
        return []

    def get_user_id(self, obj):
        return obj.user_ref.user_id if obj.user_ref else obj.user_id

    def get_user_name(self, obj):
        if obj.user_ref:
            return obj.user_ref.user_name
        user = User._default_manager.filter(user_id=obj.user_id).only('user_name').first()
        return user.user_name if user and user.user_name else obj.user_name

    def get_user_avatar(self, obj):
        return obj.avatar_url

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user_id') and request.user_id:
            return obj.likes.filter(user_id=request.user_id).exists()
        return False


class PostSerializer(serializers.ModelSerializer):
    is_liked = serializers.BooleanField(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    content = serializers.CharField(max_length=280, required=False, allow_blank=True)
    group = GroupSerializer(read_only=True)
    group_id = serializers.IntegerField(write_only=True, required=False)
    comment_count = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "group",
            "group_id",
            "user",
            "content",
            "created_at",
            "updated_at",
            "like_count",
            "is_liked",
            "attachments",
            "comment_count",
        ]
        read_only_fields = ["like_count"]

    def get_comment_count(self, obj):
        return obj.comments.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'user' not in data:
            data['user'] = UserSerializer(instance).data
        return data