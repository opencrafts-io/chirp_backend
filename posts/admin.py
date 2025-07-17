from django.contrib import admin
from .models import Attachment, Post, PostLike, PostReply

# Register your models here.
admin.site.register(Post)
admin.site.register(PostReply)
admin.site.register(Attachment)
admin.site.register(PostLike)
