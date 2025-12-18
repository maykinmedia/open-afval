from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


class PaginatedRetrieveMixin:
    """
    Retrieve a paginated model instance.
    """

    # code based on list method from the rest_framework.mixins.ListModelMixin
    def retrieve(self: GenericViewSet, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
