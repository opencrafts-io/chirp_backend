from django.contrib import admin
from .models import Conversation, ConversationMessage


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'participants', 'created_at', 'updated_at', 'last_message_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['conversation_id', 'participants']
    readonly_fields = ['conversation_id', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('messages')


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender_id', 'content_preview', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at', 'sender_id']
    search_fields = ['content', 'sender_id', 'conversation__conversation_id']
    readonly_fields = ['created_at']

    @admin.display(description='Content Preview')
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
