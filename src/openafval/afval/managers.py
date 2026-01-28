from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Q, QuerySet, Sum

if TYPE_CHECKING:
    from .models import Container, ContainerLocation, Klant, Lediging


class ContainerManager(models.Manager):
    def for_klant(self, klant: Klant) -> QuerySet[Container]:
        """
        Get unique containers for `klant` with aggregated weights.
        """
        return (
            self.filter(ledigingen__klant=klant)
            .distinct()
            .annotate(totaal_gewicht=Sum("ledigingen__gewicht", filter=Q(ledigingen__klant=klant)))
            .order_by("afval_type", "id")
        )


class ContainerLocationManager(models.Manager):
    def for_klant(self, klant: Klant) -> QuerySet[ContainerLocation]:
        """
        Get unique container locations for `klant` with aggregated weights.
        """
        return (
            self.filter(ledigingen__klant=klant)
            .distinct()
            .annotate(totaal_gewicht=Sum("ledigingen__gewicht", filter=Q(ledigingen__klant=klant)))
            .order_by("adres", "id")
        )


class KlantManager(models.Manager):
    def for_container_location(self, container_location: ContainerLocation) -> QuerySet[Klant]:
        return (
            self.filter(ledigingen__container_location=container_location)
            .distinct()
            .order_by("-geleegd_op")
        )

    def for_container(self, container: Container) -> QuerySet[Klant]:
        return self.filter(ledigingen__container=container).distinct()


class LedigingManager(models.Manager):
    def for_klant(self, klant: Klant) -> QuerySet[Lediging]:
        return self.filter(klant=klant).order_by("-geleegd_op")

    def for_date_range(self, start_date: date, end_date: date) -> QuerySet[Lediging]:
        return self.filter(geleegd_op_datum__range=[start_date, end_date])

    def from_date(self, from_date: date) -> QuerySet[Lediging]:
        return self.filter(geleegd_op_datum__gte=from_date)

    def before_date(self, before_date: date) -> QuerySet[Lediging]:
        return self.filter(geleegd_op_datum__lte=before_date)
