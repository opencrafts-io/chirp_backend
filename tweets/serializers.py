from rest_framework import serializers
from .models import Tweets

class WhitespaceAllowedCharField(serializers.CharField):
    """Custom CharField that allows whitespace-only content"""

    def __init__(self, **kwargs):
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('trim_whitespace', False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        # Convert to string and return as-is (don't strip or validate blank)
        if data is None:
            return None
        return str(data)

class StatusSerializer(serializers.ModelSerializer):
    content = WhitespaceAllowedCharField(max_length=280)
    user_id = serializers.CharField(required=False, max_length=100)

    class Meta:
        model = Tweets
        fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_content(self, value):
        """Validate tweet content"""
        # Only reject empty string, allow whitespace-only content
        if value == '':
            raise serializers.ValidationError("This field may not be blank.")

        return value

