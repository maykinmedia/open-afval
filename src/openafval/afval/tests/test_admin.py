import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from maykin_2fa.test import disable_admin_mfa

from openafval.accounts.tests.factories import UserFactory
from openafval.afval.admin import KlantAdmin
from openafval.afval.models import Klant
from openafval.afval.profiel import AfvalProfiel, KlantProfiel
from openafval.afval.profiel_display import format_afval_profiel

from .factories import (
    ContainerFactory,
    ContainerLocationFactory,
    KlantFactory,
    LedigingFactory,
)

TZ = ZoneInfo("Europe/Amsterdam")


@disable_admin_mfa()
class KlantChangelistTest(TestCase):
    def setUp(self):
        self.superuser = UserFactory.create(superuser=True)
        self.client.force_login(self.superuser)

    def test_changelist_shows_addresses_and_containers(self):
        klant = KlantFactory.create()
        loc_a = ContainerLocationFactory.create(adres="Straat 1 [1234AB AMSTERDAM]")
        loc_b = ContainerLocationFactory.create(adres="Straat 2 [5678CD ROTTERDAM]")
        container_a = ContainerFactory.create(public_container_id="CONT-A")
        container_b = ContainerFactory.create(public_container_id="CONT-B")

        LedigingFactory.create(klant=klant, container=container_a, container_location=loc_a)
        LedigingFactory.create(klant=klant, container=container_b, container_location=loc_b)
        # Second lediging for the same container/location pair must not duplicate.
        LedigingFactory.create(klant=klant, container=container_a, container_location=loc_a)

        response = self.client.get(reverse("admin:afval_klant_changelist"))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content.count(loc_a.adres), 1)
        self.assertEqual(content.count(loc_b.adres), 1)
        self.assertEqual(content.count("CONT-A"), 1)
        self.assertEqual(content.count("CONT-B"), 1)

    def test_klant_without_ledigingen_shows_dash(self):
        klant = KlantFactory.create()

        admin = KlantAdmin(Klant, None)
        obj = admin.get_queryset(None).get(pk=klant.pk)

        self.assertEqual(admin.adressen(obj), "-")
        self.assertEqual(admin.containers(obj), "-")

    def test_changelist_query_count_is_independent_of_lediging_count(self):
        # Warm up permission/content-type caches so the first measured request
        # isn't skewed by one-time setup queries.
        self.client.get(reverse("admin:afval_klant_changelist"))

        small_klant = KlantFactory.create()
        LedigingFactory.create(klant=small_klant)

        with CaptureQueriesContext(connection) as small:
            self.client.get(reverse("admin:afval_klant_changelist"))

        large_klant = KlantFactory.create()
        for _ in range(9):
            LedigingFactory.create(klant=large_klant)

        with CaptureQueriesContext(connection) as large:
            self.client.get(reverse("admin:afval_klant_changelist"))

        self.assertEqual(len(small.captured_queries), len(large.captured_queries))


@disable_admin_mfa()
class KlantSearchTest(TestCase):
    def setUp(self):
        self.superuser = UserFactory.create(superuser=True)
        self.client.force_login(self.superuser)

    def test_search_by_bsn(self):
        klant = KlantFactory.create()
        other = KlantFactory.create()

        response = self.client.get(reverse("admin:afval_klant_changelist"), {"q": klant.bsn})

        self.assertEqual(list(response.context["cl"].queryset), [klant])
        self.assertNotIn(other, response.context["cl"].queryset)

    def test_search_by_address_fragment(self):
        klant = KlantFactory.create()
        other = KlantFactory.create()
        loc = ContainerLocationFactory.create(adres="Kerkstraat 5 [1000AA AMSTERDAM]")
        LedigingFactory.create(klant=klant, container_location=loc)

        response = self.client.get(reverse("admin:afval_klant_changelist"), {"q": "Kerkstraat"})

        self.assertEqual(list(response.context["cl"].queryset), [klant])
        self.assertNotIn(other, response.context["cl"].queryset)

    def test_search_by_container_public_id(self):
        klant = KlantFactory.create()
        other = KlantFactory.create()
        container = ContainerFactory.create(public_container_id="CONT-UNIQUE")
        LedigingFactory.create(klant=klant, container=container)

        response = self.client.get(reverse("admin:afval_klant_changelist"), {"q": "CONT-UNIQUE"})

        self.assertEqual(list(response.context["cl"].queryset), [klant])
        self.assertNotIn(other, response.context["cl"].queryset)

    def test_klant_with_multiple_matching_ledigingen_appears_once(self):
        klant = KlantFactory.create()
        loc = ContainerLocationFactory.create(adres="Kerkstraat 5 [1000AA AMSTERDAM]")
        LedigingFactory.create(klant=klant, container_location=loc)
        LedigingFactory.create(klant=klant, container_location=loc)

        response = self.client.get(reverse("admin:afval_klant_changelist"), {"q": "Kerkstraat"})

        self.assertEqual(list(response.context["cl"].queryset), [klant])


@disable_admin_mfa()
class KlantDetailPageTest(TestCase):
    def test_detail_page_contains_afval_profiel_link(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()

        response = self.client.get(reverse("admin:afval_klant_change", args=[klant.pk]))

        self.assertContains(response, reverse("admin:afval_klant_afval_profiel", args=[klant.pk]))

    def test_detail_page_contains_afval_profiel_field(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()

        response = self.client.get(reverse("admin:afval_klant_change", args=[klant.pk]))

        self.assertContains(response, "Afval profiel")
        url = reverse("admin:afval_klant_afval_profiel", args=[klant.pk])
        self.assertContains(response, f'<a href="{url}">Bekijk afval profiel</a>', html=True)


@disable_admin_mfa()
class AfvalProfielViewTest(TestCase):
    def test_renders_for_superuser(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()
        loc = ContainerLocationFactory.create(adres="Dorpsstraat 12 [1234AB AMSTERDAM]")
        container = ContainerFactory.create(public_container_id="CONT-99", afval_type="gft")
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc,
            gewicht=10.5,
            kosten=Decimal("3.50"),
            geleegd_op=datetime(2026, 1, 15, 10, 30, tzinfo=TZ),
        )

        response = self.client.get(reverse("admin:afval_klant_afval_profiel", args=[klant.pk]))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Dorpsstraat 12, 1234 AB, Amsterdam", content)
        self.assertIn("CONT-99", content)
        self.assertIn("Groente, Fruit en Tuin afval (GFT)", content)
        self.assertIn("10:30", content)

    def test_404_for_unknown_uuid(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)

        response = self.client.get(reverse("admin:afval_klant_afval_profiel", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_redirected_to_login(self):
        klant = KlantFactory.create()

        response = self.client.get(reverse("admin:afval_klant_afval_profiel", args=[klant.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_staff_without_view_permission_gets_permission_denied(self):
        staff = UserFactory.create(is_staff=True)
        self.client.force_login(staff)
        klant = KlantFactory.create()

        response = self.client.get(reverse("admin:afval_klant_afval_profiel", args=[klant.pk]))

        self.assertEqual(response.status_code, 403)

    def _stub_profiel(self, klant: Klant) -> AfvalProfiel:
        return AfvalProfiel(
            klant=KlantProfiel(
                id=klant.id, bsn=klant.bsn, naam=klant.naam, totaal_kosten=Decimal(0)
            ),
            containers=[],
            container_locaties=[],
            ledigingen=[],
        )

    def test_jaar_filter_passes_start_and_einddatum_to_afval_profiel(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()
        LedigingFactory.create(klant=klant, geleegd_op=datetime(2025, 6, 1, tzinfo=TZ))

        with patch.object(
            Klant, "afval_profiel", return_value=self._stub_profiel(klant)
        ) as mock_afval_profiel:
            self.client.get(
                reverse("admin:afval_klant_afval_profiel", args=[klant.pk]), {"jaar": "2025"}
            )

        mock_afval_profiel.assert_called_once_with(startdatum="2025-01-01", einddatum="2025-12-31")

    def test_no_jaar_param_passes_no_date_filter_to_afval_profiel(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()
        LedigingFactory.create(klant=klant, geleegd_op=datetime(2025, 6, 1, tzinfo=TZ))

        with patch.object(
            Klant, "afval_profiel", return_value=self._stub_profiel(klant)
        ) as mock_afval_profiel:
            self.client.get(reverse("admin:afval_klant_afval_profiel", args=[klant.pk]))

        mock_afval_profiel.assert_called_once_with(startdatum=None, einddatum=None)

    def test_out_of_range_jaar_param_is_ignored(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()
        LedigingFactory.create(klant=klant, geleegd_op=datetime(2025, 6, 1, tzinfo=TZ))

        with patch.object(
            Klant, "afval_profiel", return_value=self._stub_profiel(klant)
        ) as mock_afval_profiel:
            self.client.get(
                reverse("admin:afval_klant_afval_profiel", args=[klant.pk]), {"jaar": "1999"}
            )

        mock_afval_profiel.assert_called_once_with(startdatum=None, einddatum=None)

    def test_renders_year_links_from_earliest_lediging_to_current_year(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()
        LedigingFactory.create(klant=klant, geleegd_op=datetime(2024, 3, 1, tzinfo=TZ))
        huidig_jaar = timezone.now().year

        response = self.client.get(reverse("admin:afval_klant_afval_profiel", args=[klant.pk]))

        self.assertContains(response, '<a href="">Alle jaren</a>')
        for jaar in range(2024, huidig_jaar + 1):
            self.assertContains(response, f'<a href="?jaar={jaar}">{jaar}</a>')

    def test_selected_year_link_is_marked_active(self):
        superuser = UserFactory.create(superuser=True)
        self.client.force_login(superuser)
        klant = KlantFactory.create()
        LedigingFactory.create(klant=klant, geleegd_op=datetime(2024, 3, 1, tzinfo=TZ))

        response = self.client.get(
            reverse("admin:afval_klant_afval_profiel", args=[klant.pk]), {"jaar": "2024"}
        )

        self.assertContains(
            response,
            '<li class="afval-profiel__jaar afval-profiel__jaar--actief">'
            '<a href="?jaar=2024">2024</a></li>',
            html=True,
        )


class FormatAfvalProfielTest(TestCase):
    def test_groups_by_location_then_container_with_totals(self):
        klant = KlantFactory.create()
        loc = ContainerLocationFactory.create(adres="Dorpsstraat 12 [1234AB AMSTERDAM]")
        container = ContainerFactory.create(public_container_id="CONT-1", afval_type="gft")
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc,
            gewicht=10.5,
            kosten=Decimal("3.50"),
            geleegd_op=datetime(2026, 1, 15, 10, 30, tzinfo=TZ),
        )

        profiel = klant.afval_profiel()
        result = format_afval_profiel(profiel)

        self.assertEqual(len(result), 1)
        location_data = result[0]
        self.assertEqual(location_data["adres"], "Dorpsstraat 12, 1234 AB, Amsterdam")
        self.assertEqual(len(location_data["containers"]), 1)

        container_data = location_data["containers"][0]
        self.assertEqual(container_data["public_container_id"], "CONT-1")
        self.assertEqual(container_data["type_label"], "Groente, Fruit en Tuin afval (GFT)")
        self.assertEqual(len(container_data["rows"]), 1)

        row = container_data["rows"][0]
        self.assertEqual(row["tijd"], "10:30")
        self.assertTrue(row["datum"].endswith("15-01-2026"))

    def test_unknown_afval_type_falls_back_to_raw_value(self):
        klant = KlantFactory.create()
        loc = ContainerLocationFactory.create(adres="Straat 1")
        container = ContainerFactory.create(afval_type="med")
        LedigingFactory.create(klant=klant, container=container, container_location=loc)

        result = format_afval_profiel(klant.afval_profiel())

        self.assertEqual(result[0]["containers"][0]["type_label"], "Medisch afval")

    def test_empty_profiel_returns_empty_list(self):
        klant = KlantFactory.create()

        result = format_afval_profiel(klant.afval_profiel())

        self.assertEqual(result, [])
