from rest_framework import serializers
from .models import Tweets

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tweets
        fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']
 
