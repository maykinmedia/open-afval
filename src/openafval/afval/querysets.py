from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet

if TYPE_CHECKING:
    from .models import Container, ContainerLocation, Klant, Lediging


class ContainerQuerySet(models.QuerySet):
    def for_klant(self, klant: Klant) -> QuerySet[Container]:
        """Get containers for a specific klant, ordered by afval_type and id."""
        return self.filter(ledigingen__klant=klant).distinct().order_by("afval_type", "id")


class ContainerLocationQuerySet(models.QuerySet):
    def for_klant(self, klant: Klant) -> QuerySet[ContainerLocation]:
        """Get container locations for a specific klant, ordered by adres and id."""
        return self.filter(ledigingen__klant=klant).distinct().order_by("adres", "id")


class LedigingQuerySet(models.QuerySet):
    def for_klant(self, klant: Klant) -> QuerySet[Lediging]:
        """Get ledigingen for a specific klant, ordered by geleegd_op descending."""
        return self.filter(klant=klant).order_by("-geleegd_op")
