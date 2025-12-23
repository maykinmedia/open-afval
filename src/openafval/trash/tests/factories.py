from collections.abc import Sequence

from django.utils import timezone

import factory.fuzzy
from faker import Faker

from ..models import (
    BagObject,
    Container,
    ContainerType,
    Emptying,
    Entity,
    EntityObjectManagement,
    Fraction,
)

fake = Faker()


class BagObjectFactory(factory.django.DjangoModelFactory[BagObject]):
    identifier = factory.Sequence(lambda n: f"BagObject-{n}")
    address = factory.Faker("address")

    class Meta:  # pyright: ignore
        model = BagObject


class EntityFactory(factory.django.DjangoModelFactory[BagObject]):
    identifier = factory.Sequence(lambda n: f"Entity-{n}")
    bsn = factory.fuzzy.FuzzyInteger(000000000, 999999999)
    name = factory.Faker("company")
    address = factory.Faker("address")
    postcode = factory.Faker("postcode")
    postcode_city = factory.LazyAttribute(lambda o: f"{o.postcode} {fake.word()}")

    class Meta:  # pyright: ignore
        model = Entity


class EntityObjectManagementFactory(
    factory.django.DjangoModelFactory[EntityObjectManagement]
):
    identifier = factory.Sequence(lambda n: f"EOM-{n}")
    entity = factory.SubFactory(EntityFactory)
    bag_object = factory.SubFactory(BagObjectFactory)
    start_date = factory.Faker("past_date", start_date="-20d")
    end_date = factory.Faker("future_date", end_date="+10d")

    class Meta:  # pyright: ignore
        model = EntityObjectManagement


class FractionFactory(factory.django.DjangoModelFactory[Fraction]):
    identifier = factory.Sequence(lambda n: f"Fraction-{n}")
    description = factory.Faker("sentence")

    class Meta:  # pyright: ignore
        model = Fraction


class ContainerTypeFactory(factory.django.DjangoModelFactory[ContainerType]):
    fraction = factory.SubFactory(FractionFactory)
    type = factory.Faker("word")
    description = factory.Faker("sentence")

    class Meta:  # pyright: ignore
        model = ContainerType


class ContainerFactory(factory.django.DjangoModelFactory[Container]):
    type = factory.SubFactory(ContainerTypeFactory)
    identifier = factory.Sequence(lambda n: f"Container-{n}")
    is_collection_container = factory.Faker("boolean")
    has_key = factory.Faker("boolean")

    class Meta:  # pyright: ignore
        model = Container


class EmptyingFactory(factory.django.DjangoModelFactory[Emptying]):
    container = factory.SubFactory(ContainerFactory)
    identifier = factory.Sequence(lambda n: f"Emptying-{n}")
    weight_dispersed = factory.LazyFunction(lambda: fake.random_number(digits=3))
    weight_none_dispersed = factory.LazyFunction(lambda: fake.random_number(digits=3))
    amount = factory.LazyFunction(lambda: fake.random_number(digits=1))
    date = factory.Faker("past_date")
    datetime = factory.Faker("past_datetime", tzinfo=timezone.get_current_timezone())
    cost_per_kilo = factory.LazyFunction(lambda: fake.random_number(digits=2))
    cost_per_emptying = factory.LazyFunction(lambda: fake.random_number(digits=4))
    share_factor = 1

    class Meta:  # pyright: ignore
        model = Emptying

    @factory.post_generation
    def entity_object_management(
        obj: Emptying,  # pyright: ignore[reportGeneralTypeIssues]
        create: bool,
        extracted: Sequence[EntityObjectManagement],
        **kwargs,
    ):
        if not create:
            return

        if extracted:
            obj.entity_object_management.set(extracted)
