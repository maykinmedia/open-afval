from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from openafval.afval.models import Container, ContainerLocation, Lediging

from .factories import (
    ContainerFactory,
    ContainerLocationFactory,
    KlantFactory,
    LedigingFactory,
)

TZ_LOCAL = "Europe/Amsterdam"


class ContainerQuerySetTest(TestCase):
    def test_for_klant_orders_by_afval_type_and_id(self):
        klant = KlantFactory.create()
        container_rest = ContainerFactory.create(afval_type="restafval")
        container_gft = ContainerFactory.create(afval_type="gft")
        location = ContainerLocationFactory.create()

        LedigingFactory.create(klant=klant, container=container_rest, container_location=location)
        LedigingFactory.create(klant=klant, container=container_gft, container_location=location)

        containers = Container.objects.for_klant(klant)

        self.assertEqual(list(containers), [container_gft, container_rest])

    def test_for_klant_isolates_containers_between_klanten(self):
        klant1 = KlantFactory.create()
        klant2 = KlantFactory.create()
        container1 = ContainerFactory.create()
        container2 = ContainerFactory.create()
        location = ContainerLocationFactory.create()

        LedigingFactory.create(klant=klant1, container=container1, container_location=location)
        LedigingFactory.create(klant=klant2, container=container2, container_location=location)

        containers1 = Container.objects.for_klant(klant1)
        containers2 = Container.objects.for_klant(klant2)

        with self.subTest("containers for klant1"):
            self.assertEqual(containers1.count(), 1)
            self.assertEqual(containers1.first(), container1)

        with self.subTest("containers for klant2"):
            self.assertEqual(containers2.count(), 1)
            self.assertEqual(containers2.first(), container2)


class ContainerLocationQuerySetTest(TestCase):
    def test_for_klant_returns_unique_locations(self):
        klant = KlantFactory.create()
        container = ContainerFactory.create()
        location = ContainerLocationFactory.create()

        LedigingFactory.create(klant=klant, container=container, container_location=location)
        LedigingFactory.create(klant=klant, container=container, container_location=location)

        locations = ContainerLocation.objects.for_klant(klant)

        self.assertEqual(locations.count(), 1)
        self.assertEqual(locations.first(), location)

    def test_for_klant_orders_by_adres_and_id(self):
        klant = KlantFactory.create()
        container = ContainerFactory.create()
        location_a = ContainerLocationFactory.create(adres="A Street")
        location_b = ContainerLocationFactory.create(adres="B Street")

        LedigingFactory.create(klant=klant, container=container, container_location=location_b)
        LedigingFactory.create(klant=klant, container=container, container_location=location_a)

        locations = ContainerLocation.objects.for_klant(klant)

        self.assertEqual(list(locations), [location_a, location_b])

    def test_for_klant_isolates_between_klanten(self):
        klant1 = KlantFactory.create()
        klant2 = KlantFactory.create()
        container = ContainerFactory.create()
        location1 = ContainerLocationFactory.create()
        location2 = ContainerLocationFactory.create()

        LedigingFactory.create(klant=klant1, container=container, container_location=location1)
        LedigingFactory.create(klant=klant2, container=container, container_location=location2)

        locations1 = ContainerLocation.objects.for_klant(klant1)
        locations2 = ContainerLocation.objects.for_klant(klant2)

        self.assertEqual(locations1.count(), 1)
        self.assertEqual(locations2.count(), 1)
        self.assertEqual(locations1.first(), location1)
        self.assertEqual(locations2.first(), location2)


class LedigingQuerySetTest(TestCase):
    def test_for_klant_filters_by_klant(self):
        klant1 = KlantFactory.create()
        klant2 = KlantFactory.create()
        container = ContainerFactory.create()
        location = ContainerLocationFactory.create()

        lediging1 = LedigingFactory.create(
            klant=klant1, container=container, container_location=location
        )
        lediging2 = LedigingFactory.create(
            klant=klant2, container=container, container_location=location
        )

        result = Lediging.objects.for_klant(klant1)

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), lediging1)
        self.assertNotIn(lediging2, result)

    def test_for_klant_orders_by_geleegd_op_descending(self):
        klant = KlantFactory.create()
        container = ContainerFactory.create()
        location = ContainerLocationFactory.create()

        lediging_old = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            geleegd_op=datetime(2026, 1, 10, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        lediging_new = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            geleegd_op=datetime(2026, 1, 20, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        result = Lediging.objects.for_klant(klant)

        self.assertEqual(list(result), [lediging_new, lediging_old])
