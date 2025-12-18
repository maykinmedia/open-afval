from rest_framework.test import APIClient

from .factories import TokenAuthFactory


class TokenAuthMixin:
    client: APIClient

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.token_auth = TokenAuthFactory.create()

    def setUp(self):
        super().setUp()

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_auth.token}")
