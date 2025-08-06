from django.db import models
from django.core.exceptions import ValidationError

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
    file_size = models.BigIntegerField(null=True, blank=True)  # Track file size
    original_filename = models.CharField(max_length=255, null=True, blank=True)  # Keep original name
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
    user_id = models.CharField(max_length=100)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    like_count = models.PositiveIntegerField(default=0)

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

    def __str__(self):
        return f"{self.user_id}: {self.content}..."

class PostLike(models.Model):
    user_id = models.CharField(max_length=100)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'post')

    def __str__(self):
        return f"Like by {self.user_id} on post {self.post}"

class PostReply(models.Model):
    parent_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='replies')
    user_id = models.CharField(max_length=100)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self) -> str:
        return f"Reply by {self.user_id} to post: {self.parent_post.content}..."