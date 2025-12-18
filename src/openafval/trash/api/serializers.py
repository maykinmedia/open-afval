from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


def NumberString(value: str):
    if not value.isdigit():
        raise serializers.ValidationError(_("The string may only contain numbers."))


class LedigingSerializer(serializers.Serializer):
    tijdstip = serializers.DateTimeField()
    gewicht = serializers.FloatField()


class ContainersSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        validators=[NumberString], help_text=_("The ID of the container.")
    )
    type = serializers.CharField(help_text=_("The type of container."))
    totaal_gewicht = serializers.FloatField(
        help_text=_(
            "The total weight of all the time the container has been "
            "emptied in the last 12 months."
        )
    )
    ledigingen = LedigingSerializer(
        many=True, help_text=_("The lediging of the container per date time.")
    )


class BagObjectSerializer(serializers.Serializer):
    object_id = serializers.CharField(
        validators=[NumberString], help_text=_("The ID of the Bag Object.")
    )
    object_address = serializers.CharField(
        help_text=_("The address of the Bag Object.")
    )
    totaal_gewicht = serializers.FloatField(
        help_text=_("The total weight of all the emptied containers from an entity.")
    )
    containers = ContainersSerializer(
        many=True, help_text=_("The containers from a Bag Object.")
    )
