from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class BagObject(models.Model):
    id: int
    identifier = models.CharField(
        _("identifier"),
        help_text=_("Imported identifier for the BAG object."),
        max_length=255,
        unique=True,
    )
    address = models.CharField(
        _("address"),
        help_text=_("The address of the BAG object."),
        max_length=80,
        blank=True,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("BAG object")
        verbose_name_plural = _("BAG objects")

    def __str__(self):
        return self.address or self.identifier


class Entity(models.Model):
    id: int  # implicitly provided by django
    identifier = models.CharField(
        _("identifier"),
        help_text=_("Imported identifier for the entity (subject)."),
        max_length=255,
        unique=True,
    )
    bsn = models.CharField(
        _("bsn"),
        help_text=_("The BSN of the entity (subject)."),
        max_length=9,
        blank=True,
    )
    name = models.CharField(
        _("name"),
        help_text=_(
            "The name of the entity (subject), this can be a "
            "person, organisation, company, etc."
        ),
        max_length=120,
        blank=True,
    )
    address = models.CharField(
        _("address"),
        help_text=_("The address of the entity (subject)."),
        max_length=120,
        blank=True,
    )
    postcode_city = models.CharField(
        _("postcode + city"),
        help_text=_("The postcode with the city/town of the entity (subject)."),
        max_length=120,
        blank=True,
    )
    postcode = models.CharField(
        _("postcode"),
        help_text=_("The postcode of the entity (subject)."),
        max_length=6,
        blank=True,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("entity")
        verbose_name_plural = _("entities")

    def __str__(self):
        return self.bsn or self.name


class EntityObjectManagement(models.Model):
    id: int
    identifier = models.CharField(
        _("identifier"),
        help_text=_("Imported identifier for the entity linked to BAG object."),
        max_length=255,
        unique=True,
    )
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    bag_object = models.ForeignKey(BagObject, on_delete=models.CASCADE)
    start_date = models.DateField(
        _("start date"),
        help_text=_(
            "The start date of when the entity (subject) is in use of the BAG object."
        ),
        null=True,
    )
    end_date = models.DateField(
        _("end date"),
        help_text=_(
            "The date of when the entity (subject) is no longer in use of the "
            "BAG object."
        ),
        null=True,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("entity object management")
        verbose_name_plural = _("entity object managements")

    def __str__(self):
        return f"{self.entity} - {self.bag_object}"


class Fraction(models.Model):
    id: int
    identifier = models.CharField(
        _("identifier"),
        help_text=_("Imported identifier for the Fraction."),
        max_length=255,
        unique=True,
    )
    description = models.TextField(
        _("description"),
        help_text=_("The description of the Fraction."),
    )

    class Meta:  # pyright: ignore
        verbose_name = _("faction")
        verbose_name_plural = _("fractions")

    def __str__(self):
        return self.description


class ContainerType(models.Model):
    id: int
    fraction = models.ForeignKey(
        Fraction,
        verbose_name=_("fraction"),
        help_text=_("The fraction of the container."),
        on_delete=models.CASCADE,
        null=True,
    )
    type = models.CharField(
        _("type"),
        max_length=120,
        help_text=_("The type of the container."),
        unique=True,
    )
    description = models.TextField(
        _("description"),
        help_text=_("The description of the container."),
        blank=True,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("container type")
        verbose_name_plural = _("container types")

    def __str__(self):
        return f"{self.type} - {self.description}"


class Container(models.Model):
    id: int
    type = models.ForeignKey(
        ContainerType,
        verbose_name=_("type"),
        help_text=_("The type of the container."),
        on_delete=models.CASCADE,
        null=True,
    )
    identifier = models.CharField(
        _("identifier"),
        help_text=_("Imported identifier for the Container."),
        max_length=255,
        unique=True,
    )
    is_collection_container = models.BooleanField(
        _("is collection container"),
        help_text=_("Whether the container has a collection container."),
        default=False,
    )
    has_key = models.BooleanField(
        _("has a key"),
        help_text=_("Whether the container has a key."),
        default=False,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("container")
        verbose_name_plural = _("containers")

    def __str__(self):
        return self.identifier


class Emptying(models.Model):
    id: int
    container = models.ForeignKey(
        Container,
        verbose_name=_("container"),
        help_text=_("The container which was emptied."),
        on_delete=models.CASCADE,
    )
    entity_object_management = models.ManyToManyField(
        EntityObjectManagement,
        verbose_name=_("entity/object management"),
        help_text=_("The entity/object connection that this emptying is tied to."),
    )
    identifier = models.CharField(
        _("identifier"),
        help_text=_("Imported identifier for the Emptying."),
        max_length=255,
        unique=True,
    )
    weight_dispersed = models.CharField(
        _("weight dispersed"),
        help_text=_("The dispersed weight of the container that got dumped."),
        max_length=20,
        blank=True,
    )
    weight_none_dispersed = models.CharField(
        _("weight none dispersed"),
        help_text=_("The none dispersed weight of the container that got dumped."),
        max_length=20,
        blank=True,
    )
    amount = models.IntegerField(
        _("amount"),
        help_text=_("The amount of times the container needed to be dumped to empty."),
        default=1,
    )
    date = models.DateField(
        _("date"),
        help_text=_("The date of the emptying."),
    )
    datetime = models.DateTimeField(
        _("datetime"),
        help_text=_("The datetime of the emptying."),
    )
    cost_per_kilo = models.FloatField(
        _("cost per kilo"),
        help_text=_("The cost per kilo of weight dumped."),
        default=0.0,
    )
    cost_per_emptying = models.FloatField(
        _("cost per emptying"),
        help_text=_("The cost of this specific emptying."),
        default=0.0,
    )
    share_factor = models.IntegerField(
        _("share factor"),
        help_text=_("The factor the emptying is shared among entities."),
        default=1,
    )

    class Meta:  # pyright: ignore
        verbose_name = _("emptying")
        verbose_name_plural = _("emptying's")

    def __str__(self):
        return f"{self.identifier} - ({self.entity_object_management}/{self.container})"
