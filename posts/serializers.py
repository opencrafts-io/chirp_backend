from rest_framework import serializers
from .models import Attachment, Post, PostReply, PostLike


class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "attachment_type", "file_url", "file_size_mb", "original_filename", "created_at"]

    def get_file_url(self, obj):
        """Generate the full URL for the file"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return obj.get_file_size_mb()


class PostSerializer(serializers.ModelSerializer):
    is_liked = serializers.BooleanField(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    content = serializers.CharField(max_length=280, required=False, allow_blank=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "user_id",
            "content",
            "created_at",
            "updated_at",
            "like_count",
            "is_liked",
            "attachments",
        ]
        read_only_fields = ["user_id", "like_count"]


class PostReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = PostReply
        fields = ('id', 'parent_post', 'user_id', 'content', 'created_at', 'updated_at')
        read_only_fields = ['user_id', 'parent_post']