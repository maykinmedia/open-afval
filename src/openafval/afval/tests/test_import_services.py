from io import StringIO

from django.test import TestCase

from openafval.afval.models import Container, ContainerLocation, Klant, Lediging
from openafval.afval.services.import_services import import_from_csv_stream


class ImportFromCSVStreamTests(TestCase):
    def test_import_with_all_columns_populated(self):
        """Test importing CSV data with all columns properly populated."""
        csv_header = (
            "SUBJECTID;BSN;SUBJECTNAAM;OBJECTID;OBJECTADRES;CONTAINERID;"
            "SLEUTELNUMMER;VERZAMELCONTAINER_J_N;CONTAINERSOORT;LEDIGINGID;"
            "GEWICHT_ONVERDEELD;GEWICHT_VERDEELD;LEDIGINGSMOMENT"
        )
        csv_rows = [
            "SUBJ001;123456782;Jan Jansen;OBJ001;Straat 1;CONT001;KEY001;"
            "N;GFT;LED001;10.5;10.5;2024-01-15 10:30:00",
            "SUBJ002;987654321;Piet Pietersen;OBJ002;Laan 2;CONT002;;"
            "J;Restafval;LED002;20.0;20.0;2024-01-16 14:45:00",
            "SUBJ001;123456782;Jan Jansen;OBJ001;Straat 1;CONT003;KEY002;"
            "N;GFT;LED003;15.0;15.0;2024-01-17 09:00:00",
        ]
        csv_data = "\n".join([csv_header] + csv_rows)

        stream = StringIO(csv_data)

        import_from_csv_stream(
            stream,
            # Make sure we are chunking the input
            chunk_size=2,
        )

        # Verify Klanten were created (2 unique subjects)
        self.assertEqual(Klant.objects.count(), 2)
        klant1 = Klant.objects.get(bsn="123456782")
        self.assertEqual(klant1.naam, "Jan Jansen")
        klant2 = Klant.objects.get(bsn="987654321")
        self.assertEqual(klant2.naam, "Piet Pietersen")

        # Verify ContainerLocations were created (2 unique objects)
        self.assertEqual(ContainerLocation.objects.count(), 2)
        location1 = ContainerLocation.objects.get(adres="Straat 1")
        self.assertIsNotNone(location1)
        location2 = ContainerLocation.objects.get(adres="Laan 2")
        self.assertIsNotNone(location2)

        # Verify Containers were created (3 unique containers)
        self.assertEqual(Container.objects.count(), 3)
        gft_containers = Container.objects.filter(afval_type="gft")
        self.assertEqual(gft_containers.count(), 2)
        rest_containers = Container.objects.filter(afval_type="restafval")
        self.assertEqual(rest_containers.count(), 1)
        container_with_key = Container.objects.filter(heeft_sleutel=True)
        self.assertEqual(container_with_key.count(), 2)
        verzamelcontainers = Container.objects.filter(is_verzamelcontainer=True)
        self.assertEqual(verzamelcontainers.count(), 1)

        # Verify Ledigingen were created (3 ledigingen)
        self.assertEqual(Lediging.objects.count(), 3)
        ledigingen = Lediging.objects.all().order_by("gewicht")
        self.assertEqual(ledigingen[0].gewicht, 10.5)
        self.assertEqual(ledigingen[1].gewicht, 15.0)
        self.assertEqual(ledigingen[2].gewicht, 20.0)

    def test_import_filters_null_bsn_and_ledigingsmoment(self):
        """Test that rows with null BSN or LEDIGINGSMOMENT are excluded."""
        csv_header = (
            "SUBJECTID;BSN;SUBJECTNAAM;OBJECTID;OBJECTADRES;CONTAINERID;"
            "SLEUTELNUMMER;VERZAMELCONTAINER_J_N;CONTAINERSOORT;LEDIGINGID;"
            "GEWICHT_ONVERDEELD;GEWICHT_VERDEELD;LEDIGINGSMOMENT"
        )
        csv_rows = [
            "SUBJ001;123456782;Jan Jansen;OBJ001;Straat 1;CONT001;KEY001;"
            "N;GFT;LED001;10.5;10.5;2024-01-15 10:30:00",
            "SUBJ002;;Piet Pietersen;OBJ002;Laan 2;CONT002;;"
            "J;Restafval;LED002;20.0;20.0;2024-01-16 14:45:00",
            "SUBJ003;111111111;Maria Meijer;OBJ003;Plein 3;CONT003;KEY003;N;GFT;LED003;15.0;15.0;",
            "SUBJ004;;Anne de Vries;OBJ004;Weg 4;CONT004;;N;Restafval;LED004;25.0;25.0;",
        ]
        csv_data = "\n".join([csv_header] + csv_rows)

        stream = StringIO(csv_data)
        import_from_csv_stream(stream)

        # Only the first row should be imported
        # (has both BSN and LEDIGINGSMOMENT)
        # Row 2: missing BSN -> excluded
        # Row 3: missing LEDIGINGSMOMENT -> excluded
        # Row 4: missing both -> excluded

        # Verify only 1 Klant was created
        self.assertEqual(Klant.objects.count(), 1)
        klant = Klant.objects.first()
        self.assertEqual(klant.bsn, "123456782")
        self.assertEqual(klant.naam, "Jan Jansen")

        # Verify only 1 ContainerLocation was created
        self.assertEqual(ContainerLocation.objects.count(), 1)
        location = ContainerLocation.objects.first()
        self.assertEqual(location.adres, "Straat 1")

        # Verify only 1 Container was created
        self.assertEqual(Container.objects.count(), 1)
        container = Container.objects.first()
        self.assertEqual(container.afval_type, "gft")
        self.assertFalse(container.is_verzamelcontainer)
        self.assertTrue(container.heeft_sleutel)

        # Verify only 1 Lediging was created
        self.assertEqual(Lediging.objects.count(), 1)
        lediging = Lediging.objects.first()
        self.assertEqual(lediging.gewicht, 10.5)
        self.assertEqual(lediging.klant, klant)
        self.assertEqual(lediging.container_location, location)
        self.assertEqual(lediging.container, container)
