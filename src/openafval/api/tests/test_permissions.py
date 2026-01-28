from django.urls import path

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.test import (
    APITestCase,
    URLPatternsTestCase,
)

from ..authorization import TokenAuthentication
from ..permissions import TokenAuthPermission
from .factories import TokenAuthFactory


class TestAutorizationAndPermissionView(views.APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (TokenAuthPermission,)

    """
    A simple ViewSet for listing or retrieving users.
    """

    def get(self, request):
        return Response(status=status.HTTP_200_OK)

    def post(self, request):
        return Response(status=status.HTTP_201_CREATED)

    def put(self, request, pk=None):
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, pk=None):
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApiTokenAuthorizationAndPermissionTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("whatever", TestAutorizationAndPermissionView.as_view()),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.token = TokenAuthFactory.create().token

    def test_get_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.get("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.get("/whatever", headers={"Authorization": "Token broken"})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("with token"):
            response = self.client.get(
                "/whatever",
                headers={"Authorization": f"Token {self.token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.post("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.post("/whatever", headers={"Authorization": "Token broken"})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("with token"):
            response = self.client.post(
                "/whatever",
                headers={"Authorization": f"Token {self.token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_put_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.put("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.put("/whatever", headers={"Authorization": "Token broken"})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("with token"):
            response = self.client.put(
                "/whatever",
                headers={"Authorization": f"Token {self.token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.delete("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.delete("/whatever", headers={"Authorization": "Token broken"})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("with token"):
            response = self.client.delete(
                "/whatever",
                headers={"Authorization": f"Token {self.token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
