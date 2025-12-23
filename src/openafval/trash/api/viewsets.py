import json
from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet

from openafval.accounts.models import User

from .filters import BagBsnFilterSet
from .serializers import BagObjectSerializer


@extend_schema(tags=[_("Bag Objects")])  # pyright: ignore[reportArgumentType]
@extend_schema_view(
    list=extend_schema(
        summary=_("List all Bag objects with all the emptying's."),
        description=_(
            "A paginated list of all bag objects with the time "
            "the containers got emptied."
        ),
    ),
)
class BagBsnViewSet(ListModelMixin, GenericViewSet):
    # TODO: replace fake queryset mention
    queryset = User.objects.none()
    serializer_class = BagObjectSerializer
    filterset_class = BagBsnFilterSet

    # TODO: Remove this once we use real data
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

    # TODO: Remove this once we use real data
    def filter_queryset(self, queryset):
        return queryset
