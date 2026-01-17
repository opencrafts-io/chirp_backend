from django.core.files.storage import default_storage
from django.db import models

from communities.models import Community
from users.models import User
from utils.uploads import get_post_attachment_path


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
    file = models.FileField(upload_to=get_post_attachment_path)
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
                if hasattr(self.file, "name"):
                    default_storage.delete(self.file.name)
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
        """
        Return a human-readable representation of the post.

        Returns:
            str: The post's title followed by "by" and the author; if the title is empty or None, "Post" is used in place of the title.
        """
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
        """
        Return a human-readable representation of the comment.

        Returns:
            A string in the format "Comment by <author> on <post>" describing the comment's author and associated post.
        """
        return f"Comment by {self.author} on {self.post}"

    @property
    def is_root(self) -> bool:
        """
        Indicates whether the comment is top-level (has no parent).

        Returns:
            True if the comment has no parent, False otherwise.
        """
        return self.parent is None

    @property
    def depth(self):
        """
        Return the nesting level of this comment within its thread.

        Returns:
            int: Depth of the comment where 0 indicates a top-level (root) comment.
        """
        depth = 0
        parent = self.parent
        while parent:
            depth += 1
            parent = parent.parent
        return depth

    def get_all_replies(self, max_depth: int = 3, _current_depth: int = 0):
        """
        Collects nested reply Comment instances up to a specified nesting depth.

        Parameters:
                max_depth (int): Maximum levels of nested replies to include (default 3). A value of N includes replies up to N levels deep.
                _current_depth (int): Internal recursion depth counter; not intended for external callers.

        Returns:
                list: A flat list of reply Comment instances (including nested replies) up to the specified depth.
        """
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
