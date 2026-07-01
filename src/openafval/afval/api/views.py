from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import views
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from openafval.afval.constants import AfvalTypeChoices
from openafval.afval.models import Klant

from .serializers import AfvalProfielSerializer

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
        klant = get_object_or_404(Klant, bsn=bsn)
        params = request.GET

        startdatum = params.get("startdatum")
        einddatum = params.get("einddatum")
        afval_type = params.get("afval-type")

        errors = {}
        if startdatum and parse_date(startdatum) is None:
            errors["startdatum"] = _("Enter a valid date in YYYY-MM-DD format.")
        if einddatum and parse_date(einddatum) is None:
            errors["einddatum"] = _("Enter a valid date in YYYY-MM-DD format.")
        if afval_type and afval_type not in AfvalTypeChoices.values:
            errors["afval-type"] = _(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {"value": afval_type}
        if errors:
            raise ValidationError(errors)

        profiel = klant.afval_profiel(
            startdatum=startdatum,
            einddatum=einddatum,
            afval_type=afval_type,
            container_locaties=params.getlist("adres") or None,
        )

        try:
            serializer = AfvalProfielSerializer(profiel)
        except (KeyError, AttributeError, TypeError) as exc:
            logger.exception("Serialization for afval profiel failed")
            raise APIException(
                "Internal error building afval profiel. Please contact support."
            ) from exc

        return Response(serializer.data)
