import os
from datetime import timedelta

from django.db import transaction
from django.forms import fields
from django.utils import timezone
from rest_framework import serializers
from django.conf import settings

from communities.models import Community
from communities.serializers import CommunitySerializer
from users.serializers import UserSerializer
from .models import (
    Attachment,
    Post,
    Comment,
    Poll,
    PollOption,
    PollVote,
    PostView,
    PostVotes,
)
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
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
                validated_data["attachment_type"] = "image"
            elif file_extension in [".mp4", ".avi", ".mov", ".mkv"]:
                validated_data["attachment_type"] = "video"
            elif file_extension in [".mp3", ".wav", ".aac", ".ogg"]:
                validated_data["attachment_type"] = "audio"
            else:
                validated_data["attachment_type"] = "file"
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


class PollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ["id", "text", "position", "vote_count"]
        read_only_fields = ["id", "vote_count"]
        extra_kwargs = {"position": {"required": False}}


class PollSerializer(serializers.ModelSerializer):
    """
    Read/write representation of a poll.

    On read it includes the requesting user's selection as `my_votes`; on
    write (nested inside PostSerializer) it validates the draft and creates
    the poll with its options. Ids are assigned by the server and option
    positions are re-sequenced to 0..n-1 in the order given.
    """

    MIN_QUESTION_LENGTH = 3
    MIN_DURATION = timedelta(minutes=5)

    post = serializers.PrimaryKeyRelatedField(read_only=True)
    options = PollOptionSerializer(many=True)
    my_votes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = [
            "id",
            "post",
            "question",
            "allows_multiple",
            "is_anonymous",
            "ends_at",
            "total_votes",
            "my_votes",
            "options",
        ]
        read_only_fields = ["id", "post", "total_votes", "my_votes"]

    def get_my_votes(self, poll: Poll):
        """
        Option ids the requesting user has selected. Uses the `my_vote_rows`
        prefetch from `PostQuerySet.with_polls` when present; otherwise falls
        back to a query keyed on `request.user_id`.
        """
        rows = getattr(poll, "my_vote_rows", None)
        if rows is not None:
            return [row.option_id for row in rows]

        request = self.context.get("request")
        user_id = getattr(request, "user_id", None) if request else None
        if not user_id:
            return []
        return list(
            PollVote.objects.filter(poll=poll, user_id=user_id)
            .order_by("option__position")
            .values_list("option_id", flat=True)
        )

    def validate_question(self, value: str) -> str:
        question = value.strip()
        if len(question) < self.MIN_QUESTION_LENGTH:
            raise serializers.ValidationError(
                f"Question must be at least {self.MIN_QUESTION_LENGTH} characters."
            )
        return question

    def validate_options(self, value):
        if len(value) < Poll.MIN_OPTIONS:
            raise serializers.ValidationError(
                f"A poll needs at least {Poll.MIN_OPTIONS} options."
            )
        if len(value) > Poll.MAX_OPTIONS:
            raise serializers.ValidationError(
                f"A poll can have at most {Poll.MAX_OPTIONS} options."
            )

        # Preserve the client's ordering (by position when given, else by
        # order of appearance) and re-sequence positions server-side.
        ordered = sorted(
            enumerate(value), key=lambda item: (item[1].get("position", item[0]), item[0])
        )
        cleaned = []
        seen = set()
        for position, (_, option) in enumerate(ordered):
            text = (option.get("text") or "").strip()
            if not text:
                raise serializers.ValidationError("Options can't be empty.")
            key = text.casefold()
            if key in seen:
                raise serializers.ValidationError(f"Duplicate option: '{text}'.")
            seen.add(key)
            cleaned.append({"text": text, "position": position})
        return cleaned

    def validate_ends_at(self, value):
        if value is not None and value < timezone.now() + self.MIN_DURATION:
            raise serializers.ValidationError(
                "End time must be at least 5 minutes in the future."
            )
        return value

    def create(self, validated_data):
        options = validated_data.pop("options")
        with transaction.atomic():
            poll = Poll.objects.create(**validated_data)
            PollOption.objects.bulk_create(
                [PollOption(poll=poll, **option) for option in options]
            )
        return poll

    def update(self, instance, validated_data):
        raise serializers.ValidationError("Polls can't be edited once created.")


class PollVoterSerializer(serializers.Serializer):
    """One voter (a user) on a poll and the options they picked."""

    user_id = serializers.UUIDField(read_only=True)
    user = UserSerializer(read_only=True)
    option_ids = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    voted_at = serializers.DateTimeField(read_only=True)


class PollVoteRequestSerializer(serializers.Serializer):
    """Body of `POST /polls/<id>/vote/`."""

    option_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    # Accepted for symmetry with the post-vote endpoint, but the acting user
    # is always taken from the authenticated request.
    voter_id = serializers.CharField(required=False, allow_blank=True)


class PostSerializer(serializers.ModelSerializer):
    # Nested for reading
    author = UserSerializer(read_only=True)
    community = CommunitySerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    poll = PollSerializer(required=False, allow_null=True)

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
            "poll",
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
        poll_data = validated_data.pop("poll", None)
        post = Post.objects.create(**validated_data)
        for attachment_data in attachments_data:
            Attachment.objects.create(post=post, **attachment_data)
        if poll_data:
            PollSerializer(context=self.context).create({**poll_data, "post": post})
        return post

    def update(self, instance, validated_data):
        attachments_data = validated_data.pop("attachments", [])
        # Polls are immutable after creation; ignore any nested payload.
        validated_data.pop("poll", None)

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
        validators = []


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
        validators = []
