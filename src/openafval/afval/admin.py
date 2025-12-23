from django.contrib import admin
from django.http import HttpRequest

from .models import Container, ContainerLocation, Klant, Lediging


class ReadOnlyMixin:
    self: admin.ModelAdmin

    def has_change_permission(self, request: HttpRequest, obj=None):
        return False

    def has_add_permission(self, request: HttpRequest):
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return False


@admin.register(ContainerLocation)
class ContainerLocationAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "adres",
    )


@admin.register(Klant)
class KlantAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("id", "bsn", "naam")


@admin.register(Container)
class ContainerAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "afval_type",
        "is_verzamelcontainer",
        "heeft_sleutel",
    )


@admin.register(Lediging)
class LedigingAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "container",
        "klant",
        "container_location",
        "gewicht",
        "geleegd_op",
    )
    fields = (
        "id",
        "container",
        "klant",
        "container_location",
        "gewicht",
        "geleegd_op",
    )
