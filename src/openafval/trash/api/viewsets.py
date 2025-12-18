import json
from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import GenericViewSet

from openafval.accounts.models import User
from openafval.api.mixins import PaginatedRetrieveMixin

from .serializers import BagObjectSerializer


@extend_schema(tags=[_("Bag Objects")])
@extend_schema_view(
    retrieve=extend_schema(
        summary=_(
            "Retrieve all Bag objects with all the emptying's from a single BSN."
        ),
        description=_(
            "A paginated list of all bag objects with the time "
            "the containers got emptied from a single BSN."
        ),
    ),
)
class BagBsnViewSet(PaginatedRetrieveMixin, GenericViewSet):
    # TODO: replace fake queryset mention
    queryset = User.objects.none()
    serializer_class = BagObjectSerializer
    lookup_field = "bsn"

    def get_queryset(self):
        file_path = Path(
            settings.DJANGO_PROJECT_DIR,
            "trash",
            "api",
            "mock_data",
            "afval-mock-data.json",
        )

        with open(file_path) as file:
            return json.load(file)
