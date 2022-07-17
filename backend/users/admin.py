from django.contrib import admin

from .models import Follow, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'username', 'first_name',
        'last_name', 'email', 'role'
    )
    list_filter = ('username', 'email')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    pass
