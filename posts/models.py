from django.db import models
from django.core.exceptions import ValidationError
import os

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
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='community_posts', default=1)
    user_id = models.CharField(max_length=100)
    user_name = models.CharField(max_length=100, default='User')
    email = models.EmailField(max_length=255, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    like_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        """Custom validation for post model"""
        super().clean()

        if not self.content:
            raise ValidationError("Content is required.")

        if len(str(self.content)) > 280:
            raise ValidationError("Content cannot exceed 280 characters.")

        if not self.user_id:
            raise ValidationError("User ID is required.")

        if len(str(self.user_id)) > 100:
            raise ValidationError("User ID cannot exceed 100 characters.")

        if not self.user_name:
            raise ValidationError("User name is required.")

        if len(str(self.user_name)) > 100:
            raise ValidationError("User name cannot exceed 100 characters.")

        if not self.group:
            raise ValidationError("Group is required.")

    def delete(self, *args, **kwargs):
        """Custom delete method to ensure all attachments are properly deleted"""
        for attachment in self.attachments.all():
            attachment.delete()

        super().delete(*args, **kwargs)

    def get_threaded_comments(self):
        """Get all comments organized in a threaded structure"""
        return self.comments.filter(parent_comment__isnull=True).prefetch_related(
            'replies', 'replies__replies', 'replies__replies__replies'
        )

    def __str__(self):
        return f"{self.user_id}: {self.content[:50]}..."

class PostLike(models.Model):
    user_id = models.CharField(max_length=100)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'post')

    def __str__(self):
        return f"Like by {self.user_id} on post {self.post}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    user_id = models.CharField(max_length=100)
    user_name = models.CharField(max_length=100, default='User')
    email = models.EmailField(max_length=255, null=True, blank=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    depth = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'parent_comment']),
            models.Index(fields=['depth']),
        ]

    def clean(self):
        """Custom validation for comment model"""
        super().clean()

        if not self.content:
            raise ValidationError("Content is required.")

        if len(str(self.content)) > 280:
            raise ValidationError("Content cannot exceed 280 characters.")

        if not self.user_name:
            raise ValidationError("User name is required.")

        if len(str(self.user_name)) > 100:
            raise ValidationError("User name cannot exceed 100 characters.")

        if self.depth > 10:
            raise ValidationError("Comment depth cannot exceed 10 levels.")

    def save(self, *args, **kwargs):
        """Auto-calculate depth if not set"""
        if self.parent_comment and not self.depth:
            self.depth = self.parent_comment.depth + 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Comment by {self.user_id} on post: {self.post.content[:50]}..."