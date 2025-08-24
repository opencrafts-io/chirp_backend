from django.contrib import admin
from .models import Group, GroupPost, GroupInvite


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator_id', 'is_private', 'member_count', 'admin_count', 'created_at')
    list_filter = ('is_private', 'created_at')
    search_fields = ('name', 'description', 'creator_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'creator_id', 'is_private')
        }),
        ('Membership', {
            'fields': ('admins', 'moderators', 'members', 'banned_users')
        }),
        ('Community Guidelines', {
            'fields': ('rules',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def member_count(self, obj):
        return len(obj.members) if obj.members else 0
    member_count.short_description = 'Members'

    def admin_count(self, obj):
        return len(obj.admins) if obj.admins else 0
    admin_count.short_description = 'Admins'


@admin.register(GroupPost)
class GroupPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user_id', 'content_preview', 'created_at')
    list_filter = ('created_at', 'group')
    search_fields = ('content', 'user_id', 'group__name')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(GroupInvite)
class GroupInviteAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'inviter_id', 'invitee_id', 'created_at')
    list_filter = ('created_at', 'group')
    search_fields = ('inviter_id', 'invitee_id', 'group__name')
