from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework

from openafval.afval.models import Container, ContainerLocation, Lediging


class ContainerFilterSet(rest_framework.FilterSet):
    afval_type = rest_framework.CharFilter(
        field_name="afval_type",
        help_text=_("Filter containers by waste type (e.g., 'gft', 'restafval')"),
    )

    class Meta:
        model = Container
        fields = []


class ContainerLocationFilterSet(rest_framework.FilterSet):
    adres = rest_framework.CharFilter(
        field_name="adres",
        help_text=_("Filter container locations by address"),
    )

    class Meta:
        model = ContainerLocation
        fields = []


class LedigingFilterSet(rest_framework.FilterSet):
    startdatum = rest_framework.DateFilter(
        field_name="geleegd_op_datum",
        lookup_expr="gte",
        help_text=_("Filter ledigingen from this date (YYYY-MM-DD)"),
    )
    einddatum = rest_framework.DateFilter(
        field_name="geleegd_op_datum",
        lookup_expr="lte",
        help_text=_("Filter ledigingen until this date (YYYY-MM-DD)"),
    )

    class Meta:
        model = Lediging
        fields = []
