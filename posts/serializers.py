from django.forms import fields
from rest_framework import serializers
from django.conf import settings

from communities.models import Community
from communities.serializers import CommunitySerializer
from users.serializers import UserSerializer
from .models import Attachment, Post, Comment, PostView, PostVotes
from users.models import User


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = "__all__"

    def create(self, validated_data):
        # Auto-populate file_size and original_filename
        file = validated_data.get("file")
        if file:
            validated_data["file_size"] = file.size
            validated_data["original_filename"] = file.name
        return super().create(validated_data)


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
        """
        Return a list of serialized reply comments for the given comment, limited to a maximum nesting depth.

        Parameters:
            obj (Comment): The comment whose direct replies should be serialized. The serializer respects and increments `context["current_depth"]` when recursing.

        Returns:
            list: Serialized reply data; returns an empty list when the maximum depth of 3 has been reached.
        """
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
    community = CommunitySerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    # Primary keys for writing and also readable
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="author"
    )
    community_id = serializers.PrimaryKeyRelatedField(
        queryset=Community.objects.all(), source="community"
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "community",
            "community_id",
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

    def create(self, validated_data):
        attachments_data = validated_data.pop("attachments", [])
        post = Post.objects.create(**validated_data)
        for attachment_data in attachments_data:
            Attachment.objects.create(post=post, **attachment_data)
        return post

    def update(self, instance, validated_data):
        attachments_data = validated_data.pop("attachments", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        existing_ids = [a.get("id") for a in attachments_data if a.get("id")]
        instance.attachments.exclude(id__in=existing_ids).delete()

        for attachment_data in attachments_data:
            attachment_id = attachment_data.get("id")
            if attachment_id:
                Attachment.objects.filter(id=attachment_id, post=instance).update(
                    **attachment_data
                )
            else:
                Attachment.objects.create(post=instance, **attachment_data)

        return instance


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
