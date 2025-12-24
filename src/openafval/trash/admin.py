from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .models import (
    BagObject,
    Container,
    ContainerType,
    Emptying,
    Entity,
    EntityObjectManagement,
)


class ReadOnlyMixin:
    self: admin.ModelAdmin

    def has_change_permission(self, request: HttpRequest, obj=None):
        return False

    def has_add_permission(self, request: HttpRequest, obj=None):
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return False


@admin.register(BagObject)
class BagObjectAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "identifier",
        "address",
    )


@admin.register(Entity)
class EntityAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("identifier", "bsn", "name")


@admin.register(EntityObjectManagement)
class EntityObjectManagementAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "identifier",
        "entity",
        "bag_object",
        "start_date",
        "end_date",
    )


@admin.register(ContainerType)
class ContainerTypeAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "type",
        "description",
        "fraction_identifier",
        "fraction_description",
    )

    def fraction_identifier(self, obj):
        return obj.fraction.identifier

    def fraction_description(self, obj):
        return obj.fraction.description


@admin.register(Container)
class ContainerAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "identifier",
        "type_text",
        "description",
        "is_collection_container",
        "has_key",
    )

    @admin.display(description=_("type"))
    def type_text(self, obj):
        return obj.type.type

    def description(self, obj):
        return obj.type.description


class EntityObjectManagementAdminInline(ReadOnlyMixin, admin.StackedInline):
    model = EntityObjectManagement.emptying_set.through  # pyright: ignore[reportAttributeAccessIssue]
    verbose_name = _("Entity Object Management")
    verbose_name_plural = _("Entity Object Management's")
    extra = 0


@admin.register(Emptying)
class EmptyingAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = (
        "identifier",
        "container",
        "weight_dispersed",
        "weight_none_dispersed",
        "amount",
        "cost_per_emptying",
        "share_factor",
        "datetime",
    )
    inlines = (EntityObjectManagementAdminInline,)
    fields = (
        "identifier",
        "container",
        "weight_dispersed",
        "weight_none_dispersed",
        "amount",
        "cost_per_kilo",
        "cost_per_emptying",
        "share_factor",
        "date",
        "datetime",
    )
