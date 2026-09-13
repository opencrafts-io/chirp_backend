from django.contrib import admin

from posts.models import Poll, PollOption, Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "title",
        "comment_count",
        "views_count",
        "upvotes",
        "downvotes",
        "created_at",
    )


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 0
    fields = ("position", "text", "vote_count")
    readonly_fields = ("vote_count",)
    ordering = ("position",)


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "post",
        "allows_multiple",
        "is_anonymous",
        "total_votes",
        "ends_at",
        "created_at",
    )
    list_filter = ("allows_multiple", "is_anonymous", "created_at")
    search_fields = ("question", "post__title")
    readonly_fields = ("total_votes", "created_at", "updated_at")
    inlines = [PollOptionInline]

    def save_related(self, request, form, formsets, change):
        # Adding/removing options through the inline cascades votes away;
        # bring the denormalized counters back in line with the vote table.
        super().save_related(request, form, formsets, change)
        form.instance.recount()


#     list_filter = ('group', 'created_at', 'user_name')
#     search_fields = ('content', 'user_name', 'user_id', 'group__name')
#     readonly_fields = ('like_count', 'created_at', 'updated_at')
#
#     fieldsets = (
#         ('Post Information', {
#             'fields': ('content', 'group', 'like_count')
#         }),
#         ('User Information', {
#             'fields': ('user_id', 'user_name', 'email', 'avatar_url')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
#
#     def content_preview(self, obj: Post) -> str:
#         return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
#     content_preview.short_description = 'Content'
#
#
# @admin.register(Comment)
# class CommentAdmin(admin.ModelAdmin):
#     list_display = ('id', 'user_name', 'user_id', 'post', 'parent_comment', 'depth', 'like_count', 'content_preview', 'created_at')
#     list_filter = ('created_at', 'user_name', 'depth', 'is_deleted')
#     search_fields = ('content', 'user_name', 'user_id', 'post__content')
#     list_select_related = ('post', 'parent_comment')
#     readonly_fields = ('like_count', 'created_at', 'updated_at')
#
#     fieldsets = (
#         ('Comment Information', {
#             'fields': ('content', 'post', 'parent_comment', 'depth', 'like_count', 'is_deleted')
#         }),
#         ('User Information', {
#             'fields': ('user_id', 'user_name', 'email', 'avatar_url')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
#
#     def content_preview(self, obj: Comment) -> str:
#         return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
#     content_preview.short_description = 'Content'
#
#
# @admin.register(Attachment)
# class AttachmentAdmin(admin.ModelAdmin):
#     list_display = ('id', 'post', 'attachment_type', 'file_size_display', 'original_filename', 'created_at')
#     list_filter = ('attachment_type', 'created_at')
#     search_fields = ('original_filename', 'post__content')
#
#     def file_size_display(self, obj):
#         return obj.get_file_size_mb()
#     file_size_display.short_description = 'File Size (MB)'
#
#
# @admin.register(PostLike)
# class PostLikeAdmin(admin.ModelAdmin):
#     list_display = ('id', 'post', 'user_id', 'created_at')
#     list_filter = ('created_at', 'user_id')
#     search_fields = ('user_id', 'post__content')
#
#
# @admin.register(CommentLike)
# class CommentLikeAdmin(admin.ModelAdmin):
#     list_display = ('id', 'comment', 'user_id', 'created_at')
#     list_filter = ('created_at', 'user_id')
#     search_fields = ('user_id', 'comment__content')
