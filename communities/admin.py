from django.contrib import admin
from .models import Community, CommunityMembership


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


@admin.register(CommunityMembership)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "community",
        "user",
        "role",
        "banned",
        "banned_by",
        "joined_at",
    )

# @admin.register(CommunityInvite)
# class CommunityInviteAdmin(admin.ModelAdmin):
#     list_display = ('id', 'group', 'inviter_id', 'invitee_id', 'created_at')
#     list_filter = ('created_at', 'group')
#     search_fields = ('inviter_id', 'invitee_id', 'group__name')
