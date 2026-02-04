import random
from datetime import UTC

import factory.fuzzy
from faker import Faker

from ..models import (
    Container,
    ContainerLocation,
    Klant,
    Lediging,
)

fake = Faker()


def _generate_bsn():
    """Generate a valid BSN using 11-proof check."""

    digits = [random.randint(1, 9)]  # First digit 1-9
    digits.extend([random.randint(0, 9) for _ in range(7)])  # Next 7 digits 0-9

    # Calculate the 9th digit using 11-proof
    # The formula: sum of (digit * multiplier) for positions 9,8,7,6,5,4,3,2
    # where last digit uses -1 as multiplier
    total = sum(d * m for d, m in zip(digits, range(9, 1, -1), strict=True))

    # Find the last digit that makes total % 11 == 0
    for last_digit in range(10):
        if (total - last_digit) % 11 == 0:
            digits.append(last_digit)
            break

    return "".join(map(str, digits))


class ContainerLocationFactory(factory.django.DjangoModelFactory[ContainerLocation]):
    adres = factory.Faker("address")

    class Meta:
        model = ContainerLocation


class KlantFactory(factory.django.DjangoModelFactory[Klant]):
    bsn = factory.LazyFunction(_generate_bsn)
    naam = factory.Faker("company")

    class Meta:
        model = Klant


class ContainerFactory(factory.django.DjangoModelFactory[Container]):
    afval_type = factory.Iterator(["gft", "restafval"])
    is_verzamelcontainer = factory.Faker("boolean")
    heeft_sleutel = factory.Faker("boolean")

    class Meta:
        model = Container


class LedigingFactory(factory.django.DjangoModelFactory[Lediging]):
    container_location = factory.SubFactory(ContainerLocationFactory)
    klant = factory.SubFactory(KlantFactory)
    container = factory.SubFactory(ContainerFactory)
    gewicht = factory.LazyFunction(lambda: fake.random_number(digits=3))
    geleegd_op = factory.Faker("past_datetime", tzinfo=UTC)

    class Meta:
        model = Lediging
