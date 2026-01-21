import json
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from openafval.api.tests.mixins import TokenAuthMixin


class BagApiTests(TokenAuthMixin, APITestCase):
    def _get_mock_response(self):
        file_path = Path(
            settings.DJANGO_PROJECT_DIR,
            "afval",
            "api",
            "mock_data",
            "afval-mock-data.json",
        )

        with open(file_path) as file:
            return json.load(file)

    def test_no_credentials_given(self):
        list_url = reverse("api:bag-list")
        self.client.credentials(HTTP_AUTHORIZATION="")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_bag_objects(self):
        list_url = reverse("api:bag-list")

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"], self._get_mock_response())

    def test_list_bag_objects_bsn_filter(self):
        list_url = reverse("api:bag-list")

        response = self.client.get(list_url, {"bsn": "1123456780"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"], self._get_mock_response())
