from rest_framework import serializers
from .models import Message

class WhitespaceAllowedCharField(serializers.CharField):
    """Custom CharField that allows whitespace-only content"""

    def __init__(self, **kwargs):
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('trim_whitespace', False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data is None:
            return None
        return str(data)

class MessageSerializer(serializers.ModelSerializer):
    content = WhitespaceAllowedCharField()
    sender_id = serializers.CharField(read_only=True, max_length=100)

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        read_only_fields = ['id', 'sender_id', 'created_at']

    def validate_content(self, value):
        """Validate message content"""
        # Only reject empty string, allow whitespace-only content
        if value == '':
            raise serializers.ValidationError("This field may not be blank.")

        return value

    def validate_recipient_id(self, value):
        """Validate recipient_id"""
        if not value or not value.strip():
            raise serializers.ValidationError("Recipient ID cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError("Recipient ID cannot exceed 100 characters.")

        return value