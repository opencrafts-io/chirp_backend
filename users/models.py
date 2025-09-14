from django.db import models


class User(models.Model):
    user_id = models.CharField(max_length=100, unique=True, primary_key=True)
    user_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['user_name']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.user_name} ({self.user_id})"