from __future__ import annotations

from collections import OrderedDict

from django.db.models import Count, Max, Min, QuerySet, Sum
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import views
from rest_framework.response import Response

from openafval.afval.models import Container, ContainerLocation, Klant, Lediging

from .serializers import (
    AfvalProfielSerializer,
    ContainerLocationSerializer,
    ContainerSerializer,
    KlantSerializer,
    LedigingSerializer,
    SummarySerializer,
)


class AfvalProfielAPIView(views.APIView):
    """
    Retrieve the complete afval profiel for a klant by BSN.

    This is a detail view that returns a single 'afval profiel' object
    with data about container locations, containers, and ledigingen.
    """

    def _get_summary(
        self,
        ledigingen: QuerySet[Lediging],
        aantal_containers: int,
        aantal_container_locaties: int,
    ) -> dict:
        """
        Compute summary statistics for the klant's afval profiel.

        Includes total weights, counts, and date ranges.
        """
        # Get aggregations for all ledigingen
        stats = ledigingen.aggregate(
            totaal_gewicht=Sum("gewicht"),
            aantal_ledigingen=Count("id"),
            eerste_lediging=Min("geleegd_op"),
            laatste_lediging=Max("geleegd_op"),
        )

        # Aggregate weight per afval type (reuse existing queryset)
        per_type = (
            ledigingen.values("container__afval_type")
            .annotate(gewicht=Sum("gewicht"))
            .order_by("container__afval_type")
        )

        totaal_per_type = {
            item["container__afval_type"]: item["gewicht"] for item in per_type
        }

        return {
            "totaal_gewicht": stats["totaal_gewicht"] or 0.0,
            "totaal_gewicht_per_afval_type": totaal_per_type,
            "aantal_ledigingen": stats["aantal_ledigingen"],
            "aantal_containers": aantal_containers,
            "aantal_container_locaties": aantal_container_locaties,
            "periode": {
                "eerste_lediging": stats["eerste_lediging"],
                "laatste_lediging": stats["laatste_lediging"],
            }
            if stats["eerste_lediging"]
            else None,
        }

    @extend_schema(
        summary=_("Retrieve afval profiel for a klant by BSN"),
        tags=["Afval profiel"],
        description=_(
            "Returns the complete afval profiel for a specific klant. "
            "This is a detail view returning a single profiel object with "
            "summary statistics, all containers, all container locations, and "
            "ledigingen."
        ),
        responses={
            200: AfvalProfielSerializer,
            404: None,
        },
    )
    def get(self, request, bsn: str, *args, **kwargs):
        # Get resources
        klant = get_object_or_404(Klant, bsn=bsn)
        containers = Container.objects.for_klant(klant)
        container_locaties = ContainerLocation.objects.for_klant(klant)
        ledigingen = Lediging.objects.for_klant(klant)

        # Serialize (this evaluates the querysets)
        klant_data = KlantSerializer(klant).data
        containers_data = ContainerSerializer(containers, many=True).data
        container_locaties_data = ContainerLocationSerializer(
            container_locaties, many=True
        ).data
        ledigingen_data = LedigingSerializer(ledigingen, many=True).data

        # Calculate summary (using counts from already-evaluated data)
        summary_data = self._get_summary(
            ledigingen, len(containers_data), len(container_locaties_data)
        )
        summary_serialized = SummarySerializer(summary_data).data

        response_data = OrderedDict(
            [
                ("klant", klant_data),
                ("summary", summary_serialized),
                ("containers", containers_data),
                ("container_locaties", container_locaties_data),
                ("ledigingen", ledigingen_data),
            ]
        )

        return Response(response_data)
