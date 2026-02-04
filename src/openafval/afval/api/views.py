from __future__ import annotations

from collections import OrderedDict

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import views
from rest_framework.response import Response

from openafval.afval.models import Container, ContainerLocation, Klant, Lediging

from .filters import (
    ContainerFilterSet,
    ContainerLocationFilterSet,
    LedigingFilterSet,
)
from .serializers import (
    AfvalProfielSerializer,
    ContainerLocationSerializer,
    ContainerSerializer,
    KlantSerializer,
    LedigingSerializer,
)


class AfvalProfielAPIView(views.APIView):
    @extend_schema(
        summary=_("Retrieve afval profiel for a klant by BSN"),
        tags=["Afval profiel"],
        description=_(
            "Returns the complete afval profiel for a specific klant. "
            "This is a detail view returning a single profiel object with "
            "all containers, all container locations, and ledigingen."
        ),
        parameters=[
            OpenApiParameter(
                name="afval-type",
                type=str,
                description="Filter containers by waste type (e.g., 'gft', 'restafval')",
                required=False,
            ),
            OpenApiParameter(
                name="adres",
                type=str,
                description="Filter container locations by address",
                required=False,
            ),
            OpenApiParameter(
                name="startdatum",
                type=str,
                description="Filter ledigingen from this date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="einddatum",
                type=str,
                description="Filter ledigingen until this date (YYYY-MM-DD)",
                required=False,
            ),
        ],
        responses={
            200: AfvalProfielSerializer,
            404: None,
        },
    )
    def get(self, request, bsn: str, *args, **kwargs):
        # collect resources
        klant = get_object_or_404(Klant, bsn=bsn)

        containers_qs = Container.objects.for_klant(klant)
        container_locaties_qs = ContainerLocation.objects.for_klant(klant)
        ledigingen_qs = Lediging.objects.for_klant(klant)

        # apply filters (normalize params)
        query_params = request.GET.copy()
        if "afval-type" in query_params:
            query_params.setlist("afval_type", query_params.pop("afval-type"))

        containers_filter = ContainerFilterSet(query_params, queryset=containers_qs)
        container_locaties_filter = ContainerLocationFilterSet(
            query_params, queryset=container_locaties_qs
        )
        ledigingen_filter = LedigingFilterSet(query_params, queryset=ledigingen_qs)

        containers = containers_filter.qs
        container_locaties = container_locaties_filter.qs
        ledigingen = ledigingen_filter.qs

        start_date = query_params.get("startdatum")
        end_date = query_params.get("einddatum")

        containers = containers.with_aggregate_weights(
            klant=klant, start_date=start_date, end_date=end_date
        )
        container_locaties = container_locaties.with_aggregate_weights(
            klant=klant, start_date=start_date, end_date=end_date
        )

        # serialize for response
        klant_data = KlantSerializer(klant).data
        containers_data = ContainerSerializer(containers, many=True).data
        container_locaties_data = ContainerLocationSerializer(container_locaties, many=True).data
        ledigingen_data = LedigingSerializer(ledigingen, many=True).data

        response_data = OrderedDict(
            [
                ("klant", klant_data),
                ("containers", containers_data),
                ("container_locaties", container_locaties_data),
                ("ledigingen", ledigingen_data),
            ]
        )

        return Response(response_data)
