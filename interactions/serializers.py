from rest_framework import serializers
from .models import Block, Report

class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ['id', 'blocked_user', 'blocked_community', 'block_type', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        request = self.context.get('request')
        user_id = getattr(request, 'user_id', None)

        blocked_user = data.get('blocked_user')
        if blocked_user and str(blocked_user.user_id) == str(user_id):
            raise serializers.ValidationError({"error": "You cannot block yourself."})

        if Block.objects.filter(
            blocker__user_id=user_id, 
            blocked_user=blocked_user,
            block_type=data.get('block_type')
        ).exists():
            raise serializers.ValidationError({"error": "This block already exists."})

        return data

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id', 'reported_user', 'reported_post', 'reported_comment', 
            'reported_community', 'report_type', 'reason', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']