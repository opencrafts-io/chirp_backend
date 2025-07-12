from rest_framework import serializers
from .models import Tweets, TweetReply

class WhitespaceAllowedCharField(serializers.CharField):
    """Custom CharField that allows whitespace-only content"""

    def __init__(self, **kwargs):
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('trim_whitespace', False)
        super().__init__(**kwargs)


class ReplySerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(read_only=True)

    class Meta:
        model = TweetReply
        fields = ['id', 'user_id', 'content', 'created_at']
        read_only_fields = ['id', 'user_id', 'created_at']

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Reply content cannot be empty")
        if len(value) > 280:
            raise serializers.ValidationError("Reply content cannot be more than 280 characters")
        return value

class StatusSerializer(serializers.ModelSerializer):
    content = WhitespaceAllowedCharField(max_length=280, required=False, allow_null=True)
    user_id = serializers.CharField(read_only=True, max_length=100)
    replies = ReplySerializer(many=True, read_only=True)
    reply_count = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False)


    class Meta:
        model = Tweets
        fields = ['id', 'user_id', 'content', 'image', 'created_at', 'updated_at', 'replies', 'reply_count']
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at', 'replies', 'reply_count']

    def get_reply_count(self, obj):
        return obj.replies.count()

    def validate(self, attrs):
        """
        Check that at least one of 'content' or 'image' is present.
        """
        content = attrs.get('content')
        image = attrs.get('image')

        if not content and not image:
            raise serializers.ValidationError("At least one of 'content' or 'image' must be provided.")

        return attrs