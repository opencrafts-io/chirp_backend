from django.db import models


class MessageAttachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("file", "File"),
    ]

    message = models.ForeignKey(
        "Message", on_delete=models.CASCADE, related_name="attachments"
    )
    attachment_type = models.CharField(
        max_length=10, choices=ATTACHMENT_TYPE_CHOICES, default="image"
    )
    file = models.FileField(upload_to="message_attachments/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attachment_type} for message {self.message}"


class Message(models.Model):
    sender_id = models.CharField(max_length=100)
    recipient_id = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_id} to {self.recipient_id}: {self.content}..."
