from django.contrib import admin
from .models import CustomUser, Group, Ticket

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'group')
    list_filter = ('role', 'group')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Group)
admin.site.register(Ticket)
