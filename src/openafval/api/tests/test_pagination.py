from django.urls import path

from rest_framework import generics, serializers, status
from rest_framework.test import APITestCase, URLPatternsTestCase

from ..pagination import DynamicPageSizePagination


class TestDynamicPageSizePaginationSerializer(serializers.Serializer):
    foo = serializers.CharField()


class TestDynamicPageSizePaginationViewSet(generics.ListAPIView):
    serializer_class = TestDynamicPageSizePaginationSerializer
    pagination_class = DynamicPageSizePagination
    authentication_classes = ()
    permission_classes = ()

    # overwrite get_queryset to simulate real data of 200 rows
    def get_queryset(self):
        return [{"foo": f"bar-{num}"} for num in range(200)]


class DynamicPageSizePaginationTest(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("pagination", TestDynamicPageSizePaginationViewSet.as_view()),
    ]

    def test_get_default_pagination(self):
        response = self.client.get("/pagination")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 200)
        self.assertEqual(len(data["results"]), 10)
        self.assertTrue(data["next"])
        self.assertIsNone(data["previous"])

    def test_alter_page_size(self):
        with self.subTest("no page defined"):
            response = self.client.get("/pagination", {"pageSize": 50})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 200)
            self.assertEqual(len(data["results"]), 50)
            self.assertTrue(data["next"])
            self.assertIsNone(data["previous"])

        with self.subTest("page 1"):
            response = self.client.get("/pagination", {"pageSize": 50, "page": 1})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 200)
            self.assertEqual(len(data["results"]), 50)
            self.assertTrue(data["next"])
            self.assertIsNone(data["previous"])

        with self.subTest("page 2"):
            response = self.client.get("/pagination", {"pageSize": 50, "page": 2})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 200)
            self.assertEqual(len(data["results"]), 50)
            self.assertTrue(data["next"])
            self.assertTrue(data["previous"])

        with self.subTest("last page"):
            response = self.client.get("/pagination", {"pageSize": 50, "page": 4})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 200)
            self.assertEqual(len(data["results"]), 50)
            self.assertIsNone(data["next"])
            self.assertTrue(data["previous"])

    def test_page_size_succeed_max_size(self):
        response = self.client.get("/pagination", {"pageSize": 120})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 200)
        self.assertEqual(len(data["results"]), 100)
