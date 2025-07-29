from django.db import models
from django.core.exceptions import ValidationError

class Attachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
    ]

    post = models.ForeignKey(
        "Post", on_delete=models.CASCADE, related_name="attachments"
    )
    attachment_type = models.CharField(
        max_length=10, choices=ATTACHMENT_TYPE_CHOICES, default="image"
    )
    file = models.FileField(upload_to="attachments/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attachment_type} for post {self.post}"


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
        return f"{self.user_id}: {self.content[:50]}..."

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
        return f"Reply by {self.user_id}: to post {self.parent_post.content}"