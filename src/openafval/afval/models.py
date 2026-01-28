import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import TruncDate
from django.utils.translation import gettext_lazy as _

from vng_api_common.fields import BSNField

from .constants import AfvalTypeChoices
from .managers import (
    ContainerLocationManager,
    ContainerManager,
    KlantManager,
    LedigingManager,
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

    objects = ContainerLocationManager()

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

    objects = KlantManager()

    class Meta:  # pyright: ignore
        verbose_name = _("eigenaar")
        verbose_name_plural = _("eigenaren")

    def __str__(self) -> str:
        return self.naam


class Container(AfvalBaseModel):
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

    objects = ContainerManager()

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

    objects = LedigingManager()

    class Meta:  # pyright: ignore
        verbose_name = _("lediging")
        verbose_name_plural = _("ledigingen")

    def __str__(self) -> str:
        return (
            f"Lediging {str(self.id)}: {str(self.container)} "
            f"emptied on {str(self.geleegd_op_datum)}"
        )
