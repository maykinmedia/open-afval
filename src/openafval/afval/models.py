from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, assert_never

if TYPE_CHECKING:
    from .profiel import AfvalProfiel

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import QuerySet, Sum
from django.db.models.functions import TruncDate
from django.utils.translation import gettext_lazy as _

from vng_api_common.fields import BSNField

from .constants import AfvalTypeChoices
from .querysets import (
    ContainerLocationQuerySet,
    ContainerQuerySet,
    LedigingQuerySet,
)


class AfvalBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # audit timestamps for tracking when data was imported and/or changed
    aangemaakt_op = models.DateTimeField(_("aangemaakt op"), auto_now_add=True)
    gewijzigd_op = models.DateTimeField(_("gewijzigd op"), auto_now=True)

    class Meta:
        abstract = True


class ContainerLocation(AfvalBaseModel):
    adres = models.CharField(
        verbose_name=_("adres"),
        help_text=_("Het adres van een afval container."),
        max_length=80,
        blank=True,
    )

    objects = ContainerLocationQuerySet.as_manager()

    class Meta:  # pyright: ignore
        verbose_name = _("Locatie van een afval container")

    def __str__(self) -> str:
        return self.adres or str(self.id)


class Klant(AfvalBaseModel):
    bsn = BSNField(
        verbose_name=_("bsn"),
        unique=True,
        help_text=_("De BSN van de klant."),
    )
    naam = models.CharField(
        verbose_name=_("naam"),
        help_text=_("De naam van de klant, dit kan een persoon, organisatie, bedrijf, etc. zijn."),
        max_length=120,
        blank=True,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("eigenaar")
        verbose_name_plural = _("eigenaren")

    def __str__(self) -> str:
        return self.naam

    def afval_profiel(
        self,
        *,
        startdatum: str | None = None,
        einddatum: str | None = None,
        afval_type: str | None = None,
        container_locaties: QuerySet | list[uuid.UUID] | list[str] | None = None,
    ) -> AfvalProfiel:
        from .profiel import (
            AfvalProfiel,
            ContainerLocatieProfiel,
            ContainerProfiel,
            KlantProfiel,
            LedigingProfiel,
        )

        ledigingen_qs = Lediging.objects.for_klant(self)
        if startdatum:
            ledigingen_qs = ledigingen_qs.filter(geleegd_op_datum__gte=startdatum)
        if einddatum:
            ledigingen_qs = ledigingen_qs.filter(geleegd_op_datum__lte=einddatum)
        if afval_type:
            ledigingen_qs = ledigingen_qs.filter(container__afval_type=afval_type)

        containers_qs = Container.objects.for_klant(self)
        if afval_type:
            containers_qs = containers_qs.filter(afval_type=afval_type)

        match container_locaties:
            case QuerySet():
                container_locaties_qs = container_locaties
                ledigingen_qs = ledigingen_qs.filter(container_location__in=container_locaties_qs)
            case [uuid.UUID() as first, *_] | [str() as first, *_]:
                field = "pk__in" if isinstance(first, uuid.UUID) else "adres__in"
                container_locaties_qs = ContainerLocation.objects.for_klant(self).filter(
                    **{field: container_locaties}
                )
                ledigingen_qs = ledigingen_qs.filter(container_location__in=container_locaties_qs)
            case [] | None:
                container_locaties_qs = ContainerLocation.objects.for_klant(self)
            case _:
                assert_never(container_locaties)

        # Clear the default -geleegd_op ordering once; without this Django includes
        # the ordering field in GROUP BY and returns one row per lediging instead of
        # one row per container/location.
        ledigingen_qs = ledigingen_qs.order_by()

        container_totals = {
            row["container_id"]: row
            for row in ledigingen_qs.values("container_id").annotate(
                totaal_gewicht=Sum("gewicht"),
                totaal_kosten=Sum("kosten"),
            )
        }
        location_totals = {
            row["container_location_id"]: row
            for row in ledigingen_qs.values("container_location_id").annotate(
                totaal_gewicht=Sum("gewicht"),
                totaal_kosten=Sum("kosten"),
            )
        }
        klant_totaal_kosten = ledigingen_qs.aggregate(totaal=Sum("kosten"))["totaal"] or Decimal(
            "0"
        )

        return AfvalProfiel(
            klant=KlantProfiel(
                id=self.id,
                bsn=self.bsn,
                naam=self.naam,
                totaal_kosten=klant_totaal_kosten,
            ),
            containers=[
                ContainerProfiel(
                    id=c.id,
                    public_container_id=c.public_container_id,
                    afval_type=c.afval_type,
                    is_verzamelcontainer=c.is_verzamelcontainer,
                    heeft_sleutel=c.heeft_sleutel,
                    totaal_gewicht=container_totals.get(c.id, {}).get("totaal_gewicht")
                    or Decimal("0"),
                    totaal_kosten=container_totals.get(c.id, {}).get("totaal_kosten")
                    or Decimal("0"),
                )
                for c in containers_qs
            ],
            container_locaties=[
                ContainerLocatieProfiel(
                    id=loc.id,
                    adres=loc.adres,
                    totaal_gewicht=location_totals.get(loc.id, {}).get("totaal_gewicht")
                    or Decimal("0"),
                    totaal_kosten=location_totals.get(loc.id, {}).get("totaal_kosten")
                    or Decimal("0"),
                )
                for loc in container_locaties_qs
            ],
            ledigingen=[
                LedigingProfiel(
                    id=led.id,
                    container_location=led.container_location_id,
                    klant=led.klant_id,
                    container=led.container_id,
                    gewicht=led.gewicht,
                    geleegd_op=led.geleegd_op,
                    kosten=led.kosten,
                )
                for led in ledigingen_qs.order_by("-geleegd_op")
            ],
        )


class Container(AfvalBaseModel):
    public_container_id = models.CharField(
        verbose_name=_("public container ID"),
        help_text=_("De externe container-ID zoals bij de leverancier bekend is."),
        max_length=64,
        blank=True,
    )
    afval_type = models.CharField(
        verbose_name=_("afvaltype"),
        max_length=20,
        choices=AfvalTypeChoices.choices,
        help_text=_("Het type afval dat de container bevat"),
    )
    is_verzamelcontainer = models.BooleanField(
        verbose_name=_("is verzamelcontainer"),
        help_text=_("Of de container een verzamelcontainer is."),
        default=False,
    )
    heeft_sleutel = models.BooleanField(
        verbose_name=_("heeft sleutel"),
        help_text=_("Of de container een sleutel heeft."),
        default=False,
    )

    objects = ContainerQuerySet.as_manager()

    class Meta:  # pyright: ignore
        verbose_name = _("container")
        verbose_name_plural = _("containers")

    def __str__(self) -> str:
        return str(self.id)


class Lediging(AfvalBaseModel):
    container_location = models.ForeignKey(
        ContainerLocation,
        verbose_name=_("container location"),
        on_delete=models.CASCADE,
        related_name="ledigingen",
    )
    klant = models.ForeignKey(
        Klant,
        verbose_name=_("klant"),
        on_delete=models.CASCADE,
        related_name="ledigingen",
    )
    container = models.ForeignKey(
        Container,
        verbose_name=_("container"),
        help_text=_("De container die geleegd is."),
        on_delete=models.CASCADE,
        related_name="ledigingen",
    )
    gewicht = models.FloatField(
        verbose_name=_("gewicht"),
        help_text=_("De gewicht van de lediging."),
        validators=[MinValueValidator(0)],
    )
    geleegd_op = models.DateTimeField(
        verbose_name=_("geleegd op"),
        help_text=_("De datum en tijd van de lediging."),
    )
    geleegd_op_datum = models.GeneratedField(
        expression=TruncDate("geleegd_op"),
        output_field=models.DateField(),
        db_persist=True,
        db_index=True,
    )
    kosten = models.DecimalField(
        verbose_name=_("kosten"),
        help_text=_("De kosten van de lediging"),
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    objects = LedigingQuerySet.as_manager()

    class Meta:  # pyright: ignore
        verbose_name = _("lediging")
        verbose_name_plural = _("ledigingen")

    def __str__(self) -> str:
        return (
            f"Lediging {str(self.id)}: {str(self.container)} "
            f"emptied on {str(self.geleegd_op_datum)}"
        )
