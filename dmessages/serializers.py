from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'recipient_id', 'content', 'created_at']
        read_only_fields = ['id', 'sender_id', 'created_at']