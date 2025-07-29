from rest_framework import serializers
from .models import Message, MessageAttachment

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ["id", "attachment_type", "file", "created_at"]


class WhitespaceAllowedCharField(serializers.CharField):
    """Custom CharField that allows whitespace-only content"""

    def __init__(self, **kwargs):
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('trim_whitespace', False)
        super().__init__(**kwargs)

    def to_internal_value(self, data: str | None) -> str:
        if data is None:
            raise serializers.ValidationError("This field may not be null.")
        return str(data)

class MessageSerializer(serializers.ModelSerializer):
    content = WhitespaceAllowedCharField(required=False)
    sender_id = serializers.CharField(read_only=True, max_length=100)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at', 'attachments']
        read_only_fields = ['id', 'sender_id', 'created_at']

    def validate_content(self, value):
        """Validate message content"""
        if not value and (not self.instance or not self.instance.attachments.exists()):
            raise serializers.ValidationError("Message content cannot be empty if there are no attachments.")
        return value

    def validate_recipient_id(self, value):
        """Validate recipient_id"""
        if not value or not value.strip():
            raise serializers.ValidationError("Recipient ID cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Recipient ID cannot exceed 100 characters.")

        return value