from rest_framework.test import APIClient

from .factories import TokenAuthFactory


class TokenAuthMixin:
    client: APIClient

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # pyright: ignore[reportAttributeAccessIssue]

        cls.token_auth = TokenAuthFactory.create()

    def setUp(self):
        super().setUp()  # pyright: ignore[reportAttributeAccessIssue]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_auth.token}")
