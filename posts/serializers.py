from django.forms import fields
from rest_framework import serializers
from django.conf import settings

from groups.models import Group
from users.serializers import UserSerializer
from .models import Attachment, Post, Comment, PostView, PostVotes
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
    author = UserSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="author"
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author_id",
            "author",
            "content",
            "created_at",
            "updated_at",
            "upvotes",
            "downvotes",
            "replies",
            "parent",
        ]

    def get_replies(self, obj):
        max_depth = 3  # set your sane limit
        current_depth = self.context.get("current_depth", 0)
        if current_depth >= max_depth:
            return []

        serializer = CommentSerializer(
            obj.replies.all(), many=True, context={"current_depth": current_depth + 1}
        )
        return serializer.data


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
            "views_count",
            "comment_count",
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


class PostVoteSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)
    voter = UserSerializer(read_only=True, allow_null=True, source="user")
    voter_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user"
    )
    post_id = serializers.PrimaryKeyRelatedField(
        queryset=Post.objects.all(), source="post"
    )

    class Meta:
        model = PostVotes
        fields = ["id", "voter", "voter_id", "post", "post_id", "value", "created_at"]
        read_only_fields = ["voter", "post", "created_at"]
