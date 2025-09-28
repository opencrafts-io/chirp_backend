from django.db import models
from django.core.exceptions import ValidationError
import os

from communities.models import Community
from users.models import User


class Attachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("file", "File"),
    ]

    post = models.ForeignKey(
        "Post", on_delete=models.CASCADE, related_name="attachments"
    )
    attachment_type = models.CharField(
        max_length=10, choices=ATTACHMENT_TYPE_CHOICES, default="image"
    )
    file = models.FileField(upload_to="attachments/")
    file_size = models.BigIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-populate file_size and original_filename if not set
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                pass  # File might not exist yet
        if self.file and not self.original_filename:
            try:
                self.original_filename = self.file.name
            except (OSError, ValueError):
                pass  # File might not exist yet
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            try:
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
            except (OSError, ValueError):
                pass
        super().delete(*args, **kwargs)

    def get_file_url(self):
        """Generate the full URL for the file"""
        if self.file:
            try:
                return self.file.url
            except (OSError, ValueError):
                return None
        return None

    def get_file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None

    def __str__(self):
        return f"{self.attachment_type} attachment for post {self.post.id}"


class Post(models.Model):
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name="community_posts",
        default=1,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posts_users",
    )
    title = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title or 'Post'} by {self.author}"

    class Meta:
        ordering = ["-created_at"]


class PostView(models.Model):
    """
    Tracks which user viewed which post and when.
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")  # optional: only one view per user counted
        ordering = ["-viewed_at"]


class PostVotes(models.Model):
    """
    Tracks upvotes/downvotes by user.
    """

    UPVOTE = 1
    DOWNVOTE = -1

    VOTE_CHOICES = [
        (UPVOTE, "Upvote"),
        (DOWNVOTE, "Downvote"),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.SmallIntegerField(choices=VOTE_CHOICES, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")  # one vote per user per post


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"

    @property
    def is_root(self) -> bool:
        """Returns True if this comment is a top-level comment"""
        return self.parent is None

    @property
    def depth(self):
        depth = 0
        parent = self.parent
        while parent:
            depth += 1
            parent = parent.parent
        return depth

    def get_all_replies(self, max_depth: int = 3, _current_depth: int = 0):
        """Recursively fetch all nested replies up to max_depth"""
        if _current_depth >= max_depth:
            return []

        all_replies = []
        for reply in self.replies.all():
            all_replies.append(reply)
            all_replies.extend(
                reply.get_all_replies(
                    max_depth=max_depth, _current_depth=_current_depth + 1
                )
            )
        return all_replies


class CommentVote(models.Model):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    is_upvote = models.BooleanField(null=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = ("comment", "user")
