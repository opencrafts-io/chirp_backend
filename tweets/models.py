from django.db import models
from django.core.exceptions import ValidationError

class Tweets(models.Model):
    user_id = models.CharField(max_length=100)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Custom validation for Tweet model"""
        super().clean()

        if not self.content:
            raise ValidationError("Content is required.")

        if len(self.content) > 280:
            raise ValidationError("Content cannot exceed 280 characters.")

        if not self.user_id:
            raise ValidationError("User ID is required.")

        if len(self.user_id) > 100:
            raise ValidationError("User ID cannot exceed 100 characters.")

    def __str__(self):
        return f"{self.user_id}: {self.content}..."

class TweetReply(models.Model):
    parent_tweet = models.ForeignKey(Tweets, on_delete=models.CASCADE, related_name='replies')
    user_id = models.CharField(max_length=100)
    content = models.TextField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Reply by {self.user_id}: to tweet {self.parent_tweet.content}"