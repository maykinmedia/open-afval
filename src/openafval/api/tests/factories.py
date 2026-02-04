import factory

from ..models import Application


class TokenAuthFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application
