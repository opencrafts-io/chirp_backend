from rest_framework import serializers
from django.conf import settings

from groups.models import Group
from users.serializers import UserSerializer
from .models import Attachment, Post, Comment, PostView
from users.models import User


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "attachment_type",
            "file_url",
            "file_size_mb",
            "original_filename",
            "created_at",
        ]

    def get_file_url(self, obj):
        """Generate the full URL for the file"""
        if obj.file:
            request = self.context.get("request")
            if request:
                url = request.build_absolute_uri(obj.file.url)
                if getattr(settings, "USE_TLS", False):
                    url = url.replace("http://", "https://")

                if "qachirp.opencrafts.io" in url and "/qa-chirp/" not in url:
                    url = url.replace("/media/", "/qa-chirp/media/")

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
    is_liked = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "content",
            "user_id",
            "user_name",
            "user_avatar",
            "created_at",
            "updated_at",
            "depth",
            "like_count",
            "is_liked",
            "replies",
        ]

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(
                obj.replies.all(), many=True, context=self.context
            ).data
        return []

    def get_user_id(self, obj):
        return obj.user_ref.user_id if obj.user_ref else obj.user_id

    def get_user_name(self, obj):
        if obj.user_ref:
            return obj.user_ref.user_name
        user = (
            User._default_manager.filter(user_id=obj.user_id).only("user_name").first()
        )
        return user.user_name if user and user.user_name else obj.user_name

    def get_user_avatar(self, obj):
        return obj.avatar_url

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user_id") and request.user_id:
            return obj.likes.filter(user_id=request.user_id).exists()
        return False


class PostSerializer(serializers.ModelSerializer):
    # Nested for reading
    author = UserSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    # Primary keys for writing and also readable
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="author"
    )
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source="group"
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "group",
            "group_id",
            "author",
            "author_id",
            "title",
            "content",
            "upvotes",
            "downvotes",
            "attachments",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "upvotes",
            "downvotes",
            "attachments",
            "comments",
            "created_at",
            "updated_at",
        ]


class PostViewSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)
    viewer = UserSerializer(read_only=True, allow_null=True, source="user")
    viewer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user"
    )
    post_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), source="post"
    )

    class Meta:
        model = PostView
        fields = ["id", "post", "post_id", "viewer", "viewer_id", "viewed_at"]
        read_only_fields = ["id", "viewed_at"]
