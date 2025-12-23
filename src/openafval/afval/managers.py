from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet

if TYPE_CHECKING:
    from .models import Container, ContainerLocation, Klant, Lediging


class ContainerLocationManager(models.Manager):
    def for_klant(self, klant: Klant) -> QuerySet[ContainerLocation]:
        return self.filter(ledigingen__klant=klant).distinct()


class ContainerManager(models.Manager):
    def for_klant(self, klant: Klant) -> QuerySet[Container]:
        return self.filter(ledigingen__klant=klant).distinct()


class KlantManager(models.Manager):
    def for_container_location(
        self, container_location: ContainerLocation
    ) -> QuerySet[Klant]:
        return self.filter(ledigingen__container_location=container_location).distinct()

    def for_container(self, container: Container) -> QuerySet[Klant]:
        return self.filter(ledigingen__container=container).distinct()


class LedigingManager(models.Manager):
    def for_klant(self, klant: Klant) -> QuerySet[Lediging]:
        return self.filter(klant=klant)

    def for_date_range(self, start_date: date, end_date: date) -> QuerySet[Lediging]:
        return self.filter(geleegd_op_datum__range=[start_date, end_date])

    def from_date(self, from_date: date) -> QuerySet[Lediging]:
        return self.filter(geleegd_op_datum__gte=from_date)

    def before_date(self, before_date: date) -> QuerySet[Lediging]:
        return self.filter(geleegd_op_datum__lte=before_date)
