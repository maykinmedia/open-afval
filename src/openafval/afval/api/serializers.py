from rest_framework import serializers


class ContainerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    public_container_id = serializers.CharField(allow_blank=True)
    afval_type = serializers.CharField()
    is_verzamelcontainer = serializers.BooleanField()
    heeft_sleutel = serializers.BooleanField()
    totaal_gewicht = serializers.FloatField()
    totaal_kosten = serializers.DecimalField(max_digits=10, decimal_places=2)


class ContainerLocationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    adres = serializers.CharField()
    totaal_gewicht = serializers.FloatField()
    totaal_kosten = serializers.DecimalField(max_digits=10, decimal_places=2)


class KlantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    bsn = serializers.CharField()
    naam = serializers.CharField()
    totaal_kosten = serializers.DecimalField(max_digits=10, decimal_places=2)


class LedigingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    container_location = serializers.UUIDField()
    klant = serializers.UUIDField()
    container = serializers.UUIDField()
    gewicht = serializers.FloatField()
    geleegd_op = serializers.DateTimeField()
    kosten = serializers.DecimalField(max_digits=10, decimal_places=2)


class AfvalProfielSerializer(serializers.Serializer):
    klant = KlantSerializer()
    containers = ContainerSerializer(many=True)
    container_locaties = ContainerLocationSerializer(many=True)
    ledigingen = LedigingSerializer(many=True)
