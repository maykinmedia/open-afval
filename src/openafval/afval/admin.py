import io
import logging
import uuid

from django import forms
from django.contrib import admin, messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from .models import Container, ContainerLocation, Klant, Lediging
from .profiel_display import format_afval_profiel
from .services.exceptions import CSVImportError
from .services.import_services import import_from_csv_stream

logger = logging.getLogger(__name__)


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV bestand",
        help_text="Upload een CSV bestand met afvalgegevens.",
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        if not csv_file.name.endswith(".csv"):
            raise forms.ValidationError("Alleen CSV bestanden zijn toegestaan.")
        return csv_file


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
    list_display = ("id", "bsn", "naam", "adressen", "containers")
    search_fields = (
        "bsn",
        "ledigingen__container_location__adres",
        "ledigingen__container__public_container_id",
    )
    change_form_template = "admin/afval/klant/change_form.html"

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        # `__gt=""` (rather than `~Q(...="")`) excludes both NULL and empty
        # values: a klant without ledigingen only has NULLs and Django compiles
        # negated lookups to also match NULL rows.
        return qs.annotate(
            _adressen=ArrayAgg(
                "ledigingen__container_location__adres",
                distinct=True,
                filter=Q(ledigingen__container_location__adres__gt=""),
            ),
            _container_ids=ArrayAgg(
                "ledigingen__container__public_container_id",
                distinct=True,
                filter=Q(ledigingen__container__public_container_id__gt=""),
            ),
        )

    @admin.display(description=_("adressen"))
    def adressen(self, obj: Klant) -> str:
        values = sorted(getattr(obj, "_adressen", None) or [])
        if not values:
            return "-"
        return format_html(
            "<ul>{}</ul>", format_html_join("", "<li>{}</li>", ((value,) for value in values))
        )

    @admin.display(description=_("containers"))
    def containers(self, obj: Klant) -> str:
        values = sorted(getattr(obj, "_container_ids", None) or [])
        if not values:
            return "-"
        return format_html(
            "<ul>{}</ul>", format_html_join("", "<li>{}</li>", ((value,) for value in values))
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<uuid:object_id>/afval-profiel/",
                self.admin_site.admin_view(self.afval_profiel_view),
                name="afval_klant_afval_profiel",
            ),
        ]
        return custom_urls + urls

    def afval_profiel_view(self, request: HttpRequest, object_id: uuid.UUID) -> HttpResponse:
        klant = get_object_or_404(Klant, pk=object_id)
        if not self.has_view_permission(request, klant):
            raise PermissionDenied

        profiel = klant.afval_profiel()
        context = {
            **self.admin_site.each_context(request),
            "title": _("Afval profiel"),
            "klant": klant,
            "container_locaties": format_afval_profiel(profiel),
        }
        return render(request, "admin/afval/klant/afval_profiel.html", context)


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
        "kosten",
    )
    fields = (
        "id",
        "container",
        "klant",
        "container_location",
        "gewicht",
        "geleegd_op",
        "kosten",
    )
    change_list_template = "admin/afval/lediging/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="afval_lediging_import_csv",
            ),
        ]
        return custom_urls + urls

    def import_csv_view(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can import CSV files.")

        if request.method == "POST":
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]

                try:
                    csv_content = csv_file.read().decode("utf-8")
                    csv_stream = io.StringIO(csv_content)

                    import_from_csv_stream(csv_stream)

                    self.message_user(
                        request,
                        "CSV import succesvol voltooid!",
                        messages.SUCCESS,
                    )
                    return redirect("admin:afval_lediging_changelist")
                except CSVImportError as exc:
                    logger.exception("CSV import failed")
                    self.message_user(
                        request,
                        f"Fout bij importeren: {exc.message}",
                        messages.ERROR,
                    )
        else:
            form = CSVImportForm()

        context = {
            "form": form,
            "title": "CSV Import",
            "site_title": self.admin_site.site_title,
            "site_header": self.admin_site.site_header,
            "has_permission": True,
        }
        return render(request, "admin/afval/import_csv.html", context)
