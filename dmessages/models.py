from django.db import models

class Message(models.Model):
    sender_id = models.CharField(max_length=100)
    recipient_id = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_id} to {self.recipient_id}: {self.content}..."
