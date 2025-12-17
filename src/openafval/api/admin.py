from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("token", "contact_person", "email", "phone_number", "created")
    readonly_fields = ("token",)
