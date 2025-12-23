import factory

from ..models import Application


class TokenAuthFactory(factory.django.DjangoModelFactory):
    class Meta:  # pyright: ignore
        model = Application
