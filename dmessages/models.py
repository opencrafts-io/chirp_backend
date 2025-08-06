from django.db import models


class MessageAttachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("file", "File"),
    ]

    message = models.ForeignKey(
        "Message", on_delete=models.CASCADE, related_name="attachments", null=True, blank=True
    )
    conversation_message = models.ForeignKey(
        "conversations.ConversationMessage", on_delete=models.CASCADE, related_name="attachments", null=True, blank=True
    )
    attachment_type = models.CharField(
        max_length=10, choices=ATTACHMENT_TYPE_CHOICES, default="image"
    )
    file = models.FileField(upload_to="message_attachments/")
    file_size = models.BigIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                pass
        if self.file and not self.original_filename:
            try:
                self.original_filename = self.file.name
            except (OSError, ValueError):
                pass
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
        if self.message:
            return f"{self.attachment_type} attachment for message {self.message.id}"
        elif self.conversation_message:
            return f"{self.attachment_type} attachment for conversation message {self.conversation_message.id}"
        return f"{self.attachment_type} attachment"


class Message(models.Model):
    conversation = models.ForeignKey('conversations.Conversation', on_delete=models.CASCADE, null=True, blank=True)
    sender_id = models.CharField(max_length=100)
    recipient_id = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender_id} to {self.recipient_id}: {self.content}..."
