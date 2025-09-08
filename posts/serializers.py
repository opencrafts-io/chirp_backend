from rest_framework import serializers
from django.conf import settings
from .models import Attachment, Post, Comment, PostLike


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


class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'content', 'user_id', 'user_name', 'user_avatar',
                 'created_at', 'updated_at', 'depth', 'replies']

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True, context=self.context).data
        return []

    def get_user_avatar(self, obj):
        return obj.avatar_url


class PostSerializer(serializers.ModelSerializer):
    is_liked = serializers.BooleanField(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    content = serializers.CharField(max_length=280, required=False, allow_blank=True)
    group = GroupSerializer(read_only=True)
    group_id = serializers.IntegerField(write_only=True, required=False, default=1)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "group",
            "group_id",
            "user_id",
            "user_name",
            "email",
            "avatar_url",
            "content",
            "created_at",
            "updated_at",
            "like_count",
            "is_liked",
            "attachments",
            "comment_count",
        ]
        read_only_fields = ["user_id", "like_count"]

    def get_comment_count(self, obj):
        return obj.comments.count()