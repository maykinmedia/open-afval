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


class PeriodeSerializer(serializers.Serializer):
    """Serializer for the period of ledigingen."""

    eerste_lediging = serializers.DateTimeField()
    laatste_lediging = serializers.DateTimeField()


class SummarySerializer(serializers.Serializer):
    """Serializer for summary statistics."""

    totaal_gewicht = serializers.FloatField()
    totaal_gewicht_per_afval_type = serializers.DictField()
    aantal_ledigingen = serializers.IntegerField()
    aantal_containers = serializers.IntegerField()
    aantal_container_locaties = serializers.IntegerField()
    periode = PeriodeSerializer(allow_null=True)


class AfvalProfielSerializer(serializers.Serializer):
    """Serializer for the complete 'Afval profiel' for a klant"""

    klant = KlantSerializer(read_only=True)
    summary = SummarySerializer(read_only=True)
    containers = ContainerSerializer(many=True, read_only=True)
    container_locaties = ContainerLocationSerializer(many=True, read_only=True)
    ledigingen = LedigingSerializer(many=True, read_only=True)
