from datetime import datetime
from zoneinfo import ZoneInfo

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from openafval.api.tests.mixins import TokenAuthMixin

from .factories import (
    ContainerFactory,
    ContainerLocationFactory,
    KlantFactory,
    LedigingFactory,
)

TZ_LOCAL = "Europe/Amsterdam"


class AfvalProfielAPITest(TokenAuthMixin, APITestCase):
    def test_missing_credentials(self):
        self.client.credentials(HTTP_AUTHORIZATION="")
        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": "123456789"}))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_klant_not_found(self):
        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": "999999999"}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_klant_with_no_ledigingen(self):
        klant = KlantFactory.create(bsn="123456789", naam="Jan Jansen")

        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": "123456789"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(
            data["klant"],
            {
                "id": str(klant.id),
                "bsn": klant.bsn,
                "naam": klant.naam,
            },
        )

        # Check collections (all empty, no pagination)
        self.assertEqual(data["containers"], [])
        self.assertEqual(data["containerLocaties"], [])
        self.assertEqual(data["ledigingen"], [])

    def test_afval_profiel_structure(self):
        klant = KlantFactory.create(bsn="123456789", naam="Jan Jansen")
        container_location = ContainerLocationFactory.create(adres="Kerkstraat 12")
        container_gft = ContainerFactory.create(afval_type="gft")
        container_rest = ContainerFactory.create(afval_type="restafval")

        # Create ledigingen
        lediging_1 = LedigingFactory.create(
            klant=klant,
            container_location=container_location,
            container=container_gft,
            gewicht=20.0,
            geleegd_op=datetime(2026, 1, 15, 10, 0, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        lediging_2 = LedigingFactory.create(
            klant=klant,
            container_location=container_location,
            container=container_gft,
            gewicht=30.0,
            geleegd_op=datetime(2026, 1, 16, 10, 0, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        lediging_3 = LedigingFactory.create(
            klant=klant,
            container_location=container_location,
            container=container_rest,
            gewicht=50.0,
            geleegd_op=datetime(2026, 1, 17, 10, 0, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(
            data["klant"],
            {
                "id": str(klant.id),
                "bsn": klant.bsn,
                "naam": klant.naam,
            },
        )

        self.assertEqual(
            data["ledigingen"],
            [
                {
                    "id": str(lediging_3.id),
                    "containerLocation": str(lediging_3.container_location.id),
                    "klant": str(lediging_3.klant.id),
                    "container": str(lediging_3.container.id),
                    "gewicht": lediging_3.gewicht,
                    "geleegdOp": lediging_3.geleegd_op.isoformat(),
                },
                {
                    "id": str(lediging_2.id),
                    "containerLocation": str(lediging_2.container_location.id),
                    "klant": str(lediging_2.klant.id),
                    "container": str(lediging_2.container.id),
                    "gewicht": lediging_2.gewicht,
                    "geleegdOp": lediging_2.geleegd_op.isoformat(),
                },
                {
                    "id": str(lediging_1.id),
                    "containerLocation": str(lediging_1.container_location.id),
                    "klant": str(lediging_1.klant.id),
                    "container": str(lediging_1.container.id),
                    "gewicht": lediging_1.gewicht,
                    "geleegdOp": lediging_1.geleegd_op.isoformat(),
                },
            ],
        )

        # Check containers with aggregations
        self.assertEqual(len(data["containers"]), 2)
        gft_container = next(c for c in data["containers"] if c["afvalType"] == "gft")
        rest_container = next(c for c in data["containers"] if c["afvalType"] == "restafval")
        self.assertEqual(
            gft_container,
            {
                "id": str(container_gft.id),
                "afvalType": container_gft.afval_type,
                "isVerzamelcontainer": container_gft.is_verzamelcontainer,
                "heeftSleutel": container_gft.heeft_sleutel,
                "totaalGewicht": 50.0,  # 20 + 30
            },
        )
        self.assertEqual(
            rest_container,
            {
                "id": str(container_rest.id),
                "afvalType": container_rest.afval_type,
                "isVerzamelcontainer": container_rest.is_verzamelcontainer,
                "heeftSleutel": container_rest.heeft_sleutel,
                "totaalGewicht": 50.0,
            },
        )

        # Check container locations with aggregations
        self.assertEqual(
            data["containerLocaties"],
            [
                {
                    "id": str(container_location.id),
                    "adres": "Kerkstraat 12",
                    "totaalGewicht": 100.0,  # 50 + 50
                }
            ],
        )

    def test_isolation_between_klanten(self):
        """
        Test that data is properly isolated between different klanten.
        """

        klant_1 = KlantFactory.create(bsn="111111111")
        klant_2 = KlantFactory.create(bsn="222222222")
        container = ContainerFactory.create(afval_type="gft")
        container_location = ContainerLocationFactory.create(adres="Kerkstraat 12")

        # Ledigingen for klant 1
        LedigingFactory.create(
            klant=klant_1,
            container=container,
            container_location=container_location,
            gewicht=100.0,
        )
        # Ledigingen for klant 2
        LedigingFactory.create(
            klant=klant_2,
            container=container,
            container_location=container_location,
            gewicht=200.0,
        )

        # Get profiel for klant 1
        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": klant_1.bsn}))
        data = response.json()

        # Should only see data for klant 1
        self.assertEqual(len(data["ledigingen"]), 1)
        self.assertEqual(len(data["containers"]), 1)
        self.assertEqual(len(data["containerLocaties"]), 1)
        self.assertEqual(data["containers"][0]["totaalGewicht"], 100.0)
        self.assertEqual(data["containerLocaties"][0]["totaalGewicht"], 100.0)

    def test_ordering(self):
        """
        Test that ledigingen are ordered by date (newest first).
        """

        klant = KlantFactory.create(bsn="123456789")
        container = ContainerFactory.create()
        container_location = ContainerLocationFactory.create()

        lediging_1 = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=container_location,
            geleegd_op=datetime(2026, 1, 10, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        lediging_2 = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=container_location,
            geleegd_op=datetime(2026, 1, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        lediging_3 = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=container_location,
            geleegd_op=datetime(2026, 1, 12, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}))

        data = response.json()

        # Should be ordered newest first
        self.assertEqual(
            data["ledigingen"],
            [
                {
                    "id": str(lediging_2.id),
                    "containerLocation": str(container_location.id),
                    "klant": str(klant.id),
                    "container": str(container.id),
                    "gewicht": lediging_2.gewicht,
                    "geleegdOp": lediging_2.geleegd_op.isoformat(),
                },
                {
                    "id": str(lediging_3.id),
                    "containerLocation": str(container_location.id),
                    "klant": str(klant.id),
                    "container": str(container.id),
                    "gewicht": lediging_3.gewicht,
                    "geleegdOp": lediging_3.geleegd_op.isoformat(),
                },
                {
                    "id": str(lediging_1.id),
                    "containerLocation": str(container_location.id),
                    "klant": str(klant.id),
                    "container": str(container.id),
                    "gewicht": lediging_1.gewicht,
                    "geleegdOp": lediging_1.geleegd_op.isoformat(),
                },
            ],
        )

    def test_multiple_container_locationen_aggregations(self):
        klant = KlantFactory.create(bsn="123456789")
        container_location_1 = ContainerLocationFactory.create(adres="Kerkstraat 12")
        container_location_2 = ContainerLocationFactory.create(adres="Hoofdweg 45")
        container_gft = ContainerFactory.create(afval_type="gft")
        container_rest = ContainerFactory.create(afval_type="restafval")

        # Ledigingen for container_location_1
        LedigingFactory.create(
            klant=klant,
            container_location=container_location_1,
            container=container_gft,
            gewicht=10.0,
        )
        LedigingFactory.create(
            klant=klant,
            container_location=container_location_1,
            container=container_gft,
            gewicht=20.0,
        )
        LedigingFactory.create(
            klant=klant,
            container_location=container_location_1,
            container=container_rest,
            gewicht=30.0,
        )

        # Ledigingen for container_location_2
        LedigingFactory.create(
            klant=klant,
            container_location=container_location_2,
            container=container_gft,
            gewicht=15.0,
        )
        LedigingFactory.create(
            klant=klant,
            container_location=container_location_2,
            container=container_rest,
            gewicht=25.0,
        )

        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}))

        data = response.json()

        # Check container locations
        self.assertEqual(len(data["containerLocaties"]), 2)
        bag_1 = next(b for b in data["containerLocaties"] if b["adres"] == "Kerkstraat 12")
        bag_2 = next(b for b in data["containerLocaties"] if b["adres"] == "Hoofdweg 45")
        self.assertEqual(
            bag_1,
            {
                "id": str(container_location_1.id),
                "adres": container_location_1.adres,
                "totaalGewicht": 60.0,  # 10 + 20 + 30
            },
        )
        self.assertEqual(
            bag_2,
            {
                "id": str(container_location_2.id),
                "adres": "Hoofdweg 45",
                "totaalGewicht": 40.0,  # 15 + 25
            },
        )

        # Check containers (across all container locations for this klant)
        self.assertEqual(len(data["containers"]), 2)
        gft = next(c for c in data["containers"] if c["afvalType"] == "gft")
        rest = next(c for c in data["containers"] if c["afvalType"] == "restafval")
        self.assertEqual(
            gft,
            {
                "id": str(container_gft.id),
                "afvalType": container_gft.afval_type,
                "isVerzamelcontainer": container_gft.is_verzamelcontainer,
                "heeftSleutel": container_gft.heeft_sleutel,
                "totaalGewicht": 45.0,  # 10 + 20 + 15
            },
        )
        self.assertEqual(
            rest,
            {
                "id": str(container_rest.id),
                "afvalType": container_rest.afval_type,
                "isVerzamelcontainer": container_rest.is_verzamelcontainer,
                "heeftSleutel": container_rest.heeft_sleutel,
                "totaalGewicht": 55.0,  # 30 + 25
            },
        )

        # Check ledigingen count
        self.assertEqual(len(data["ledigingen"]), 5)

    def test_response_contains_all_required_fields(self):
        klant = KlantFactory.create(bsn="123456789", naam="Test Klant")
        container_location = ContainerLocationFactory.create(adres="Test Straat 1")
        container = ContainerFactory.create(
            afval_type="gft", is_verzamelcontainer=True, heeft_sleutel=False
        )

        LedigingFactory.create(
            klant=klant,
            container_location=container_location,
            container=container,
            gewicht=42.5,
            geleegd_op=datetime(2026, 1, 15, 14, 30, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        response = self.client.get(reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}))

        data = response.json()

        # Check klant structure
        self.assertEqual(
            data["klant"],
            {
                "id": str(klant.id),
                "bsn": klant.bsn,
                "naam": klant.naam,
            },
        )

        # Check container structure
        self.assertEqual(
            data["containers"],
            [
                {
                    "id": str(container.id),
                    "afvalType": container.afval_type,
                    "isVerzamelcontainer": True,
                    "heeftSleutel": False,
                    "totaalGewicht": 42.5,
                }
            ],
        )

        # Check container location structure
        self.assertEqual(
            data["containerLocaties"],
            [
                {
                    "id": str(container_location.id),
                    "adres": container_location.adres,
                    "totaalGewicht": 42.5,
                }
            ],
        )

        # Check ledigingen structure
        self.assertEqual(len(data["ledigingen"]), 1)
        lediging = data["ledigingen"][0]
        self.assertEqual(lediging["containerLocation"], str(container_location.id))
        self.assertEqual(lediging["klant"], str(klant.id))
        self.assertEqual(lediging["container"], str(container.id))
        self.assertEqual(lediging["gewicht"], 42.5)
        self.assertEqual(lediging["geleegdOp"], "2026-01-15T14:30:00+01:00")

    def test_filter_by_afval_type(self):
        klant = KlantFactory.create(bsn="123456789")
        container_gft = ContainerFactory.create(afval_type="gft")
        container_rest = ContainerFactory.create(afval_type="restafval")
        location = ContainerLocationFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container_gft,
            container_location=location,
            gewicht=10.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container_rest,
            container_location=location,
            gewicht=20.0,
        )

        response = self.client.get(
            reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}),
            {"afval-type": "gft"},
        )

        data = response.json()

        self.assertEqual(len(data["containers"]), 1)
        self.assertEqual(data["containers"][0]["afvalType"], "gft")
        self.assertEqual(data["containers"][0]["totaalGewicht"], 10.0)

    def test_filter_by_adres(self):
        klant = KlantFactory.create(bsn="123456789")
        container = ContainerFactory.create()
        location_1 = ContainerLocationFactory.create(adres="Street 1")
        location_2 = ContainerLocationFactory.create(adres="Street 2")

        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location_1,
            gewicht=15.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location_2,
            gewicht=25.0,
        )

        response = self.client.get(
            reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}),
            {"adres": "Street 1"},
        )

        data = response.json()

        self.assertEqual(len(data["containerLocaties"]), 1)
        self.assertEqual(data["containerLocaties"][0]["adres"], "Street 1")
        self.assertEqual(data["containerLocaties"][0]["totaalGewicht"], 15.0)

    def test_filter_by_date_range(self):
        klant = KlantFactory.create(bsn="123456789")
        container = ContainerFactory.create()
        location = ContainerLocationFactory.create()

        lediging_in_range = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=10.0,
            geleegd_op=datetime(2026, 1, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=20.0,
            geleegd_op=datetime(2026, 2, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        response = self.client.get(
            reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}),
            {"startdatum": "2026-01-01", "einddatum": "2026-01-31"},
        )

        data = response.json()

        self.assertEqual(len(data["ledigingen"]), 1)
        self.assertEqual(data["ledigingen"][0]["id"], str(lediging_in_range.id))

    def test_filter_date_range_affects_weight_aggregation(self):
        klant = KlantFactory.create(bsn="123456789")
        container = ContainerFactory.create()
        location = ContainerLocationFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=10.0,
            geleegd_op=datetime(2026, 1, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=20.0,
            geleegd_op=datetime(2026, 2, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        response = self.client.get(
            reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}),
            {"startdatum": "2026-01-01", "einddatum": "2026-01-31"},
        )

        data = response.json()

        self.assertEqual(data["containers"][0]["totaalGewicht"], 10.0)
        self.assertEqual(data["containerLocaties"][0]["totaalGewicht"], 10.0)

    def test_multiple_filters_combined(self):
        klant = KlantFactory.create(bsn="123456789")
        container_gft = ContainerFactory.create(afval_type="gft")
        container_rest = ContainerFactory.create(afval_type="restafval")
        location_1 = ContainerLocationFactory.create(adres="Street 1")
        location_2 = ContainerLocationFactory.create(adres="Street 2")

        LedigingFactory.create(
            klant=klant,
            container=container_gft,
            container_location=location_1,
            gewicht=10.0,
            geleegd_op=datetime(2026, 1, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        LedigingFactory.create(
            klant=klant,
            container=container_rest,
            container_location=location_2,
            gewicht=20.0,
            geleegd_op=datetime(2026, 1, 20, tzinfo=ZoneInfo(TZ_LOCAL)),
        )
        LedigingFactory.create(
            klant=klant,
            container=container_gft,
            container_location=location_1,
            gewicht=30.0,
            geleegd_op=datetime(2026, 2, 15, tzinfo=ZoneInfo(TZ_LOCAL)),
        )

        response = self.client.get(
            reverse("api:afval-profiel", kwargs={"bsn": klant.bsn}),
            {
                "afval-type": "gft",
                "adres": "Street 1",
                "startdatum": "2026-01-01",
                "einddatum": "2026-01-31",
            },
        )

        data = response.json()

        with self.subTest("containers"):
            self.assertEqual(len(data["containers"]), 1)
            self.assertEqual(data["containers"][0]["afvalType"], "gft")
            self.assertEqual(data["containers"][0]["totaalGewicht"], 10.0)

        with self.subTest("containerLocaties"):
            self.assertEqual(len(data["containerLocaties"]), 1)
            self.assertEqual(data["containerLocaties"][0]["adres"], "Street 1")

        with self.subTest("ledigingen"):
            self.assertEqual(len(data["ledigingen"]), 2)
