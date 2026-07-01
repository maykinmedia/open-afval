"""
Unit tests for LedigingQuerySet.build_profiel.

These tests exercise the queryset method directly (no HTTP layer) to ensure
the aggregation logic is correct in isolation.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from openafval.afval.models import ContainerLocation
from openafval.afval.profiel import (
    AfvalProfiel,
    ContainerLocatieProfiel,
    ContainerProfiel,
    KlantProfiel,
    LedigingProfiel,
)

from .factories import (
    ContainerFactory,
    ContainerLocationFactory,
    KlantFactory,
    LedigingFactory,
)

TZ = ZoneInfo("Europe/Amsterdam")


def _build(klant, *, startdatum=None, einddatum=None, afval_type=None, adressen=None):
    return klant.afval_profiel(
        startdatum=startdatum,
        einddatum=einddatum,
        afval_type=afval_type,
        container_locaties=adressen,
    )


class BuildProfielAggregationTest(TestCase):
    """Core aggregation correctness, including the GROUP BY ordering regression."""

    def test_all_ledigingen_for_container_are_summed(self):
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container = ContainerFactory.create()

        # Three ledigingen on consecutive days — all for the same container
        l1 = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=10.0,
            kosten=1.0,
            geleegd_op=datetime(2026, 1, 1, tzinfo=TZ),
        )
        l2 = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=20.0,
            kosten=2.0,
            geleegd_op=datetime(2026, 1, 2, tzinfo=TZ),
        )
        l3 = LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=30.0,
            kosten=3.0,
            geleegd_op=datetime(2026, 1, 3, tzinfo=TZ),
        )

        profiel = _build(klant)

        self.assertEqual(
            profiel,
            AfvalProfiel(
                klant=KlantProfiel(
                    id=klant.id,
                    bsn=klant.bsn,
                    naam=klant.naam,
                    totaal_kosten=6.0,  # 1.0 + 2.0 + 3.0
                ),
                containers=[
                    ContainerProfiel(
                        id=container.id,
                        public_container_id=container.public_container_id,
                        afval_type=container.afval_type,
                        is_verzamelcontainer=container.is_verzamelcontainer,
                        heeft_sleutel=container.heeft_sleutel,
                        totaal_gewicht=60.0,  # 10.0 + 20.0 + 30.0
                        totaal_kosten=6.0,  # 1.0 + 2.0 + 3.0
                    ),
                ],
                container_locaties=[
                    ContainerLocatieProfiel(
                        id=location.id,
                        adres=location.adres,
                        totaal_gewicht=60.0,  # 10.0 + 20.0 + 30.0
                        totaal_kosten=6.0,  # 1.0 + 2.0 + 3.0
                    ),
                ],
                ledigingen=[
                    # ordered by -geleegd_op: newest first
                    LedigingProfiel(
                        id=l3.id,
                        container_location=location.id,
                        klant=klant.id,
                        container=container.id,
                        gewicht=30.0,
                        geleegd_op=l3.geleegd_op,
                        kosten=3.0,
                    ),
                    LedigingProfiel(
                        id=l2.id,
                        container_location=location.id,
                        klant=klant.id,
                        container=container.id,
                        gewicht=20.0,
                        geleegd_op=l2.geleegd_op,
                        kosten=2.0,
                    ),
                    LedigingProfiel(
                        id=l1.id,
                        container_location=location.id,
                        klant=klant.id,
                        container=container.id,
                        gewicht=10.0,
                        geleegd_op=l1.geleegd_op,
                        kosten=1.0,
                    ),
                ],
            ),
        )

    def test_location_totals_aggregate_all_ledigingen(self):
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container = ContainerFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=15.0,
            kosten=2.5,
            geleegd_op=datetime(2026, 1, 1, tzinfo=TZ),
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            gewicht=25.0,
            kosten=3.5,
            geleegd_op=datetime(2026, 1, 2, tzinfo=TZ),
        )

        profiel = _build(klant)

        self.assertEqual(len(profiel.container_locaties), 1)
        self.assertEqual(profiel.container_locaties[0].totaal_gewicht, 40.0)
        self.assertEqual(profiel.container_locaties[0].totaal_kosten, 6.0)

    def test_klant_totaal_kosten_equals_sum_of_all_ledigingen(self):
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container_a = ContainerFactory.create()
        container_b = ContainerFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container_a,
            container_location=location,
            kosten=4.0,
            gewicht=1.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container_b,
            container_location=location,
            kosten=6.0,
            gewicht=1.0,
        )

        profiel = _build(klant)

        self.assertEqual(profiel.klant.totaal_kosten, 10.0)

    def test_container_with_no_ledigingen_in_range_gets_zero_totals(self):
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container_in = ContainerFactory.create(afval_type="gft")
        container_out = ContainerFactory.create(afval_type="restafval")

        LedigingFactory.create(
            klant=klant,
            container=container_in,
            container_location=location,
            gewicht=50.0,
            kosten=5.0,
            geleegd_op=datetime(2026, 1, 15, tzinfo=TZ),
        )
        # container_out has a lediging outside the requested range
        LedigingFactory.create(
            klant=klant,
            container=container_out,
            container_location=location,
            gewicht=99.0,
            kosten=99.0,
            geleegd_op=datetime(2025, 6, 1, tzinfo=TZ),
        )

        profiel = _build(klant, startdatum="2026-01-01", einddatum="2026-01-31")

        # The out-of-range lediging must be absent from the ledigingen list
        self.assertEqual(len(profiel.ledigingen), 1)
        containers_by_type = {c.afval_type: c for c in profiel.containers}
        self.assertEqual(containers_by_type["gft"].totaal_gewicht, 50.0)
        # Out-of-range container still appears but its totals are zero
        self.assertEqual(containers_by_type["restafval"].totaal_gewicht, 0.0)
        self.assertEqual(containers_by_type["restafval"].totaal_kosten, 0.0)


class BuildProfielConsistencyTest(TestCase):
    """Totals must match the ledigingen rows returned in the same profiel."""

    def test_container_total_matches_sum_of_returned_ledigingen(self):
        """Core consistency guarantee: sum(lediging.kosten for container X)
        must equal container_X.totaal_kosten for every container."""
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container_a = ContainerFactory.create()
        container_b = ContainerFactory.create()

        for kosten in [2.0, 3.0, 5.0]:
            LedigingFactory.create(
                klant=klant,
                container=container_a,
                container_location=location,
                kosten=kosten,
                gewicht=10.0,
            )
        for kosten in [7.0, 11.0]:
            LedigingFactory.create(
                klant=klant,
                container=container_b,
                container_location=location,
                kosten=kosten,
                gewicht=10.0,
            )

        profiel = _build(klant)

        ledigingen_list = profiel.ledigingen

        for container in profiel.containers:
            expected = sum(led.kosten for led in ledigingen_list if led.container == container.id)
            self.assertAlmostEqual(
                container.totaal_kosten,
                expected,
                places=6,
                msg=f"Container {container.id} total mismatch",
            )

    def test_location_total_matches_sum_of_returned_ledigingen(self):
        klant = KlantFactory.create()
        loc_a = ContainerLocationFactory.create()
        loc_b = ContainerLocationFactory.create()
        container = ContainerFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc_a,
            kosten=4.0,
            gewicht=10.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc_a,
            kosten=6.0,
            gewicht=10.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc_b,
            kosten=9.0,
            gewicht=10.0,
        )

        profiel = _build(klant)

        ledigingen_list = profiel.ledigingen

        for locatie in profiel.container_locaties:
            expected = sum(
                led.kosten for led in ledigingen_list if led.container_location == locatie.id
            )
            self.assertAlmostEqual(
                locatie.totaal_kosten,
                expected,
                places=6,
                msg=f"Location {locatie.id} total mismatch",
            )

    def test_klant_total_matches_sum_of_returned_ledigingen(self):
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container = ContainerFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            kosten=3.0,
            gewicht=1.0,
            geleegd_op=datetime(2026, 1, 10, tzinfo=TZ),
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=location,
            kosten=7.0,
            gewicht=1.0,
            geleegd_op=datetime(2026, 2, 10, tzinfo=TZ),
        )

        profiel = _build(klant, startdatum="2026-01-01", einddatum="2026-01-31")

        total_from_rows = sum(led.kosten for led in profiel.ledigingen)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, total_from_rows, places=6)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 3.0, places=6)


class BuildProfielIsolationTest(TestCase):
    def test_other_klant_ledigingen_not_counted(self):
        klant_a = KlantFactory.create()
        klant_b = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container = ContainerFactory.create()

        LedigingFactory.create(
            klant=klant_a,
            container=container,
            container_location=location,
            gewicht=100.0,
            kosten=10.0,
        )
        LedigingFactory.create(
            klant=klant_b,
            container=container,
            container_location=location,
            gewicht=999.0,
            kosten=999.0,
        )

        profiel = _build(klant_a)

        self.assertEqual(profiel.containers[0].totaal_gewicht, 100.0)
        self.assertEqual(profiel.containers[0].totaal_kosten, 10.0)
        self.assertEqual(profiel.klant.totaal_kosten, 10.0)
        self.assertEqual(len(profiel.ledigingen), 1)


class BuildProfielEmptyTest(TestCase):
    def test_klant_with_no_ledigingen(self):
        klant = KlantFactory.create()

        profiel = _build(klant)

        self.assertEqual(profiel.containers, [])
        self.assertEqual(profiel.container_locaties, [])
        self.assertEqual(profiel.ledigingen, [])
        self.assertEqual(profiel.klant.totaal_kosten, 0.0)


class BuildProfielContainerLocatiesInputTest(TestCase):
    def setUp(self):
        self.klant = KlantFactory.create()
        self.loc_a = ContainerLocationFactory.create(adres="Amstel 200, Amsterdam")
        self.loc_b = ContainerLocationFactory.create(adres="Damrak 1, Amsterdam")
        container = ContainerFactory.create()
        LedigingFactory.create(
            klant=self.klant,
            container=container,
            container_location=self.loc_a,
            gewicht=10.0,
            kosten=1.0,
        )
        LedigingFactory.create(
            klant=self.klant,
            container=container,
            container_location=self.loc_b,
            gewicht=20.0,
            kosten=2.0,
        )

    def _profiel(self, container_locaties):
        return self.klant.afval_profiel(container_locaties=container_locaties)

    def test_all_forms_are_equivalent(self):
        forms = {
            "adres strings": [self.loc_a.adres],
            "uuid list": [self.loc_a.id],
            "queryset": ContainerLocation.objects.filter(pk=self.loc_a.pk),
        }
        results = {label: self._profiel(v).container_locaties for label, v in forms.items()}

        reference = results["adres strings"]
        for label, locaties in results.items():
            with self.subTest(form=label):
                self.assertEqual(locaties, reference)

    def test_empty_list_behaves_as_none(self):
        # [] means "no filter" — same as None, returns all locations
        profiel_none = self.klant.afval_profiel(container_locaties=None)
        profiel_empty = self.klant.afval_profiel(container_locaties=[])
        self.assertEqual(profiel_empty.container_locaties, profiel_none.container_locaties)
        self.assertEqual(profiel_empty.ledigingen, profiel_none.ledigingen)

    def test_invalid_container_locaties_type_raises(self):
        with self.assertRaises(AssertionError):
            self.klant.afval_profiel(container_locaties=42)


class BuildProfielFilterScopingTest(TestCase):
    """Totals are always sums of the ledigingen in scope — filters narrow ledigingen too."""

    def test_afval_type_scopes_ledigingen_totals(self):
        klant = KlantFactory.create()
        location = ContainerLocationFactory.create()
        container_gft = ContainerFactory.create(afval_type="gft")
        container_rest = ContainerFactory.create(afval_type="restafval")

        LedigingFactory.create(
            klant=klant,
            container=container_gft,
            container_location=location,
            kosten=3.0,
            gewicht=5.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container_rest,
            container_location=location,
            kosten=7.0,
            gewicht=10.0,
        )

        profiel = _build(klant, afval_type="gft")

        # Only GFT container appears
        self.assertEqual(len(profiel.containers), 1)
        self.assertEqual(profiel.containers[0].afval_type, "gft")
        self.assertAlmostEqual(profiel.containers[0].totaal_kosten, 3.0, places=6)
        # Location total must only include the GFT lediging, not restafval
        self.assertEqual(len(profiel.container_locaties), 1)
        self.assertAlmostEqual(profiel.container_locaties[0].totaal_kosten, 3.0, places=6)
        # The restafval lediging must be absent from the ledigingen list
        self.assertEqual(len(profiel.ledigingen), 1)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 3.0, places=6)

    def test_container_locaties_filter_scopes_ledigingen_totals(self):
        klant = KlantFactory.create()
        loc_a = ContainerLocationFactory.create()
        loc_b = ContainerLocationFactory.create()
        container = ContainerFactory.create()

        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc_a,
            kosten=4.0,
            gewicht=5.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container,
            container_location=loc_b,
            kosten=6.0,
            gewicht=8.0,
        )

        profiel = _build(klant, adressen=[loc_a.adres])

        # Only loc_a is visible; loc_b is excluded from the list
        self.assertEqual(len(profiel.container_locaties), 1)
        self.assertAlmostEqual(profiel.container_locaties[0].totaal_kosten, 4.0, places=6)
        # Container total must only include the loc_a lediging
        self.assertEqual(len(profiel.containers), 1)
        self.assertAlmostEqual(profiel.containers[0].totaal_kosten, 4.0, places=6)
        # The loc_b lediging must be absent from the ledigingen list
        self.assertEqual(len(profiel.ledigingen), 1)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 4.0, places=6)

    def test_afval_type_filter_scopes_location_totals_across_locations(self):
        """afval_type narrows location totals even when types are at different locations."""
        klant = KlantFactory.create()
        loc_gft = ContainerLocationFactory.create()
        loc_rest = ContainerLocationFactory.create()
        container_gft = ContainerFactory.create(afval_type="gft")
        container_rest = ContainerFactory.create(afval_type="restafval")

        LedigingFactory.create(
            klant=klant,
            container=container_gft,
            container_location=loc_gft,
            kosten=3.0,
            gewicht=5.0,
        )
        LedigingFactory.create(
            klant=klant,
            container=container_rest,
            container_location=loc_rest,
            kosten=7.0,
            gewicht=10.0,
        )

        profiel = _build(klant, afval_type="gft")

        # Only GFT container appears
        self.assertEqual(len(profiel.containers), 1)
        self.assertEqual(profiel.containers[0].afval_type, "gft")
        self.assertAlmostEqual(profiel.containers[0].totaal_kosten, 3.0, places=6)
        # Only the GFT lediging is in scope
        self.assertEqual(len(profiel.ledigingen), 1)
        # loc_rest has no GFT ledigingen so its total is zero;
        # it still appears in the list because the klant has a lediging there
        locaties_by_id = {loc.id: loc for loc in profiel.container_locaties}
        self.assertAlmostEqual(locaties_by_id[loc_gft.id].totaal_kosten, 3.0, places=6)
        self.assertAlmostEqual(locaties_by_id[loc_rest.id].totaal_kosten, 0.0, places=6)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 3.0, places=6)


class BuildProfielDateFilterExclusionTest(TestCase):
    """Date filters exclude ledigingen from both the list and all totals."""

    def setUp(self):
        self.klant = KlantFactory.create()
        self.location = ContainerLocationFactory.create()
        self.container = ContainerFactory.create()

    def _lediging(self, kosten, geleegd_op):
        return LedigingFactory.create(
            klant=self.klant,
            container=self.container,
            container_location=self.location,
            kosten=kosten,
            gewicht=1.0,
            geleegd_op=geleegd_op,
        )

    def test_startdatum_excludes_earlier_ledigingen(self):
        self._lediging(kosten=99.0, geleegd_op=datetime(2025, 12, 31, tzinfo=TZ))
        self._lediging(kosten=5.0, geleegd_op=datetime(2026, 1, 15, tzinfo=TZ))

        profiel = _build(self.klant, startdatum="2026-01-01")

        self.assertEqual(len(profiel.ledigingen), 1)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 5.0, places=6)
        self.assertAlmostEqual(profiel.containers[0].totaal_kosten, 5.0, places=6)
        self.assertAlmostEqual(profiel.container_locaties[0].totaal_kosten, 5.0, places=6)

    def test_einddatum_excludes_later_ledigingen(self):
        self._lediging(kosten=5.0, geleegd_op=datetime(2026, 1, 15, tzinfo=TZ))
        self._lediging(kosten=99.0, geleegd_op=datetime(2026, 2, 1, tzinfo=TZ))

        profiel = _build(self.klant, einddatum="2026-01-31")

        self.assertEqual(len(profiel.ledigingen), 1)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 5.0, places=6)
        self.assertAlmostEqual(profiel.containers[0].totaal_kosten, 5.0, places=6)
        self.assertAlmostEqual(profiel.container_locaties[0].totaal_kosten, 5.0, places=6)

    def test_date_range_excludes_both_sides(self):
        self._lediging(kosten=99.0, geleegd_op=datetime(2025, 12, 31, tzinfo=TZ))
        self._lediging(kosten=5.0, geleegd_op=datetime(2026, 1, 15, tzinfo=TZ))
        self._lediging(kosten=99.0, geleegd_op=datetime(2026, 2, 1, tzinfo=TZ))

        profiel = _build(self.klant, startdatum="2026-01-01", einddatum="2026-01-31")

        self.assertEqual(len(profiel.ledigingen), 1)
        self.assertAlmostEqual(profiel.klant.totaal_kosten, 5.0, places=6)
