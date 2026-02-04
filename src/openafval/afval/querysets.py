from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Q, QuerySet, Sum

if TYPE_CHECKING:
    from .models import Container, ContainerLocation, Klant, Lediging


class ContainerQuerySet(models.QuerySet):
    def for_klant(self, klant: Klant) -> QuerySet[Container]:
        return self.filter(ledigingen__klant=klant).distinct().order_by("afval_type", "id")

    def with_aggregate_weights(
        self, klant: Klant, start_date: str | None = None, end_date: str | None = None
    ) -> QuerySet[Container]:
        """
        Add totaal_gewicht annotation to a container queryset.

        The annotation sums weights from ledigingen for the specified klant,
        optionally filtered by date range and afval type.
        """
        lediging_filter = Q(ledigingen__klant=klant)

        if start_date and end_date:
            lediging_filter &= Q(ledigingen__geleegd_op_datum__range=[start_date, end_date])

        return self.annotate(totaal_gewicht=Sum("ledigingen__gewicht", filter=lediging_filter))


class ContainerLocationQuerySet(models.QuerySet):
    def for_klant(self, klant: Klant) -> QuerySet[ContainerLocation]:
        return self.filter(ledigingen__klant=klant).distinct().order_by("adres", "id")

    def with_aggregate_weights(
        self, klant: Klant, start_date: str | None = None, end_date: str | None = None
    ) -> QuerySet[ContainerLocation]:
        """
        Add totaal_gewicht annotation to a container location queryset.

        The annotation sums weights from ledigingen for the specified klant,
        optionally filtered by date range.
        """
        lediging_filter = Q(ledigingen__klant=klant)

        if start_date and end_date:
            lediging_filter &= Q(ledigingen__geleegd_op_datum__range=[start_date, end_date])

        return self.annotate(totaal_gewicht=Sum("ledigingen__gewicht", filter=lediging_filter))


class LedigingQuerySet(models.QuerySet):
    def for_klant(self, klant: Klant) -> QuerySet[Lediging]:
        return self.filter(klant=klant).order_by("-geleegd_op")
