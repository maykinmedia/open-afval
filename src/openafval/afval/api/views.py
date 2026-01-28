from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import views
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from openafval.afval.constants import AfvalTypeChoices
from openafval.afval.models import Container, ContainerLocation, Klant, Lediging

from .filters import (
    ContainerFilterSet,
    ContainerLocationFilterSet,
    LedigingFilterSet,
)
from .serializers import (
    AfvalProfielSerializer,
)

logger = logging.getLogger(__name__)


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
                enum=AfvalTypeChoices.values,
                description="Filter containers by waste type",
                required=False,
            ),
            OpenApiParameter(
                name="adres",
                type=str,
                description="Filter container locations by address (repeatable for multiple)",
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

        # apply filters
        containers_filter = ContainerFilterSet(request.GET, queryset=containers_qs)
        container_locaties_filter = ContainerLocationFilterSet(
            request.GET, queryset=container_locaties_qs
        )
        ledigingen_filter = LedigingFilterSet(request.GET, queryset=ledigingen_qs)

        # attach weights calculated from filtered ledigingen
        containers_filter.attach_weights(
            ledigingen_filter.qs,
            container_locaties_filter.qs if "adres" in request.GET else None,
        )
        container_locaties_filter.attach_weights(
            ledigingen_filter.qs,
            containers_filter.qs if "afval-type" in request.GET else None,
        )

        containers = containers_filter.qs
        container_locaties = container_locaties_filter.qs
        ledigingen = ledigingen_filter.qs

        # serialize for response
        try:
            serializer = AfvalProfielSerializer(
                {
                    "klant": klant,
                    "containers": containers,
                    "container_locaties": container_locaties,
                    "ledigingen": ledigingen,
                }
            )
        except (KeyError, AttributeError, TypeError) as exc:
            logger.exception("Serialization for afval profiel failed")
            raise APIException(
                "Internal error building afval profiel. Please contact support."
            ) from exc

        return Response(serializer.data)
