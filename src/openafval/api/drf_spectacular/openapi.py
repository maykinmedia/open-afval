from drf_spectacular.openapi import AutoSchema as DrfAutoSchema

from openafval.api.mixins import PaginatedRetrieveMixin


class AutoSchema(DrfAutoSchema):
    def _is_list_view(self, serializer=None) -> bool:
        is_list_view = super()._is_list_view(serializer=serializer)

        # Treat PaginatedRetrieveMixin as list view to enable pagination.
        if isinstance(self.view, PaginatedRetrieveMixin):
            return True

        return is_list_view
