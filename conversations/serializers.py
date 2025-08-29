from rest_framework import serializers
from .models import Conversation, ConversationMessage
from dmessages.serializers import MessageAttachmentSerializer


class ConversationMessageSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = ConversationMessage
        fields = ['id', 'conversation', 'sender_id', 'content', 'created_at', 'is_read', 'attachments']
        read_only_fields = ['id', 'created_at']

    def get_attachments(self, obj):
        """Get attachments with proper context for URL generation"""
        attachments = obj.attachments.all()
        return MessageAttachmentSerializer(attachments, many=True, context=self.context).data


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations (without messages)"""
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'created_at', 'updated_at',
                 'last_message_at', 'message_count', 'last_message', 'unread_count']

    def get_message_count(self, obj):
        """Get total message count for this conversation"""
        return obj.messages.count()

    def get_last_message(self, obj):
        """Get only the last message preview (not full message)"""
        last_message = obj.messages.last()
        if last_message:
            return {
                'sender_id': last_message.sender_id,
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'created_at': last_message.created_at,
                'is_read': last_message.is_read
            }
        return None

    def get_unread_count(self, obj):
        """Get unread message count for the current user"""
        user_id = self.context.get('user_id')
        if user_id:
            return obj.messages.filter(is_read=False).exclude(sender_id=user_id).count()
        return 0


class ConversationSerializer(serializers.ModelSerializer):
    """Full conversation serializer with messages (for detailed view)"""
    messages = ConversationMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'created_at', 'updated_at',
                 'last_message_at', 'messages', 'last_message', 'unread_count', 'message_count']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return ConversationMessageSerializer(last_message, context=self.context).data
        return None

    def get_unread_count(self, obj):
        user_id = self.context.get('user_id')
        if user_id:
            return obj.messages.filter(is_read=False).exclude(sender_id=user_id).count()
        return 0

    def get_message_count(self, obj):
        """Get total message count for this conversation"""
        return obj.messages.count()


class ConversationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['participants']

    def validate_participants(self, value):
        if not isinstance(value, list) or len(value) < 2:
            raise serializers.ValidationError("Participants must be a list with at least 2 users")
        return value

    def create(self, validated_data):
        # Generate a unique conversation ID
        import uuid
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        validated_data['conversation_id'] = conversation_id
        return super().create(validated_data)