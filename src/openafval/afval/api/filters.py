from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework

from openafval.afval.constants import AfvalTypeChoices


class ContainerFilterSet(rest_framework.FilterSet):
    afval_type = rest_framework.ChoiceFilter(
        field_name="afval_type",
        choices=AfvalTypeChoices.choices,
        help_text=_("Filter containers by waste type."),
    )

    def __init__(self, data=None, *args, **kwargs):
        if data is not None and "afval-type" in data:
            normalized = data.copy()
            normalized.setlist("afval_type", data.getlist("afval-type"))
            data = normalized
        super().__init__(data, *args, **kwargs)


class ContainerLocationFilterSet(rest_framework.FilterSet):
    adres = rest_framework.CharFilter(
        field_name="adres",
        help_text=_("Filter container locations by address."),
    )


class LedigingFilterSet(rest_framework.FilterSet):
    startdatum = rest_framework.DateFilter(
        field_name="geleegd_op_datum",
        lookup_expr="gte",
        help_text=_("Filter ledigingen starting from (and including) this date (YYYY-MM-DD)."),
    )
    einddatum = rest_framework.DateFilter(
        field_name="geleegd_op_datum",
        lookup_expr="lte",
        help_text=_("Filter ledigingen up to (and including) this date (YYYY-MM-DD)."),
    )
