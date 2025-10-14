from django.contrib import admin
from .models import User


# Register your models here.
@admin.register(User)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "user_id",
        "name",
        "created_at",
    )
