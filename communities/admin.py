from django.contrib import admin
from .models import Community


#
#
@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "visibility",
        "nsfw",
        "creator",
        "verified",
        "member_count",
        "moderator_count",
        "banned_users_count",
        "created_at",
        "updated_at",
    )


#     list_filter = ('is_private', 'created_at')
#     readonly_fields = ('created_at', 'updated_at')
#     actions = ['delete_selected']
#
#     # Allow deletion from admin
#     def has_delete_permission(self, request, obj=None):
#         return True
#
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('name', 'description', 'creator_id', 'creator_name', 'is_private')
#         }),
#         ('Community Branding', {
#             'fields': ('logo', 'banner'),
#             'classes': ('collapse',)
#         }),
#         ('Membership', {
#             'fields': ('moderators', 'moderator_names', 'members', 'member_names', 'banned_users', 'banned_user_names')
#         }),
#         ('Community Guidelines', {
#             'fields': ('rules',)
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
#
#     def member_count(self, obj):
#         return len(obj.members) if obj.members else 0
#
#     def moderator_count(self, obj):
#         return len(obj.moderators) if obj.moderators else 0
#
#
# @admin.register(CommunityPost)
# class CommunityPostAdmin(admin.ModelAdmin):
#     list_display = ('id', 'group', 'user_id', 'content_preview', 'created_at')
#     list_filter = ('created_at', 'group')
#     search_fields = ('content', 'user_id', 'group__name')
#
#     def content_preview(self, obj):
#         return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
#
#
# @admin.register(CommunityInvite)
# class CommunityInviteAdmin(admin.ModelAdmin):
#     list_display = ('id', 'group', 'inviter_id', 'invitee_id', 'created_at')
#     list_filter = ('created_at', 'group')
#     search_fields = ('inviter_id', 'invitee_id', 'group__name')
