from collections import OrderedDict

from django.utils.translation import gettext_lazy
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class NumPagination(PageNumberPagination):
    """
    Number Pagination
    """

    page_size = DEFAULT_PAGE_SIZE
    page_query_param = "page"
    page_size_query_param = "size"
    max_page_size = MAX_PAGE_SIZE
    invalid_page_message = gettext_lazy("Invalid Page Number")

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("total", self.page.paginator.count),
                    ("current", self.page.number),
                    ("results", data),
                ]
            )
        )
