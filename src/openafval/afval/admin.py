import io
import logging

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from .models import Container, ContainerLocation, Klant, Lediging
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
