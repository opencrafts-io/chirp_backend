from django.contrib import admin
from .models import Attachment, Post, PostLike, PostReply


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'group', 'content_preview', 'like_count', 'created_at')
    list_filter = ('group', 'created_at', 'user_id')
    search_fields = ('content', 'user_id', 'group__name')
    readonly_fields = ('like_count', 'created_at', 'updated_at')

    def content_preview(self, obj: Post) -> str:
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(PostReply)
class PostReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'parent_post', 'content_preview', 'created_at')
    list_filter = ('created_at', 'user_id')
    search_fields = ('content', 'user_id')

    def content_preview(self, obj: PostReply) -> str:
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'attachment_type', 'file_size_mb', 'original_filename', 'created_at')
    list_filter = ('attachment_type', 'created_at')
    search_fields = ('original_filename', 'post__content')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user_id', 'created_at')
    list_filter = ('created_at', 'user_id')
    search_fields = ('user_id', 'post__content')
