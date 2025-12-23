from django.utils.translation import gettext_lazy as _

from django_filters.rest_framework import FilterSet, filters


class BagBsnFilterSet(FilterSet):
    bsn = filters.CharFilter(
        help_text=_(
            "Retrieves all the bag objects container emptying's "
            "which are connected to an entities BSN."
        ),
        method="search_bsn",
    )

    # TODO: remove/improve when real data gets used.
    def search_bsn(self, queryset, name, value):
        return queryset
