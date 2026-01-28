from rest_framework import serializers

from ..models import Container, ContainerLocation, Klant, Lediging


class ContainerSerializer(serializers.ModelSerializer):
    """Container serializer with aggregated weight for specific BSN"""

    totaal_gewicht = serializers.FloatField(read_only=True)

    class Meta:  # pyright: ignore
        model = Container
        fields = (
            "id",
            "afval_type",
            "is_verzamelcontainer",
            "heeft_sleutel",
            "totaal_gewicht",
        )
        read_only_fields = fields


class ContainerLocationSerializer(serializers.ModelSerializer):
    """Container location serializer with aggregated weight for specific BSN"""

    totaal_gewicht = serializers.FloatField(read_only=True)

    class Meta:  # pyright: ignore
        model = ContainerLocation
        fields = (
            "id",
            "adres",
            "totaal_gewicht",
        )
        read_only_fields = fields


class KlantSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore
        model = Klant
        fields = (
            "id",
            "bsn",
            "naam",
        )
        read_only_fields = fields


class LedigingSerializer(serializers.ModelSerializer):
    """Lediging serializer with ID references for related objects"""

    class Meta:  # pyright: ignore
        model = Lediging
        fields = (
            "id",
            "container_location",  # UUID
            "klant",  # UUID
            "container",  # UUID
            "gewicht",
            "geleegd_op",
        )
        read_only_fields = fields


class AfvalProfielSerializer(serializers.Serializer):
    """Serializer for the complete 'Afval profiel' for a klant"""

    klant = KlantSerializer()
    containers = ContainerSerializer(many=True)
    container_locaties = ContainerLocationSerializer(many=True)
    ledigingen = LedigingSerializer(many=True)
