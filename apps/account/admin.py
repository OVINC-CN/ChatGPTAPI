from django.contrib import admin

from apps.account.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "nick_name", "user_type", "date_joined", "last_login"]
    list_filter = ["user_type"]
    search_fields = ["username", "nick_name"]
