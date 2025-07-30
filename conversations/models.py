from django.db import models


class Conversation(models.Model):
    conversation_id = models.CharField(max_length=100, unique=True)
    participants = models.JSONField()  # List of user_ids
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conversations_conversation'

    def __str__(self):
        return f"Conversation {self.conversation_id}"


class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'conversations_conversationmessage'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender_id}: {self.content}..."
