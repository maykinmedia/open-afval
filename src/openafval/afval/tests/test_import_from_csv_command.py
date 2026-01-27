import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from openafval.afval.models import Container, ContainerLocation, Klant, Lediging


class ImportFromCSVCommandTests(TestCase):
    def test_command_imports_csv_file_end_to_end(self):
        """Test that the command successfully imports a CSV file."""
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
        ]
        csv_data = "\n".join([csv_header] + csv_rows)

        # Write CSV to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.write(csv_data)
            temp_file_path = temp_file.name

        try:
            # Test with different chunk sizes
            test_cases = [
                (1, "smaller than data"),  # Forces multiple chunks
                (10000, "larger than data"),  # Single chunk
            ]

            for chunk_size, description in test_cases:
                with self.subTest(chunk_size=description):
                    # Call the management command with specified chunk size
                    call_command(
                        "import_from_csv",
                        "--file",
                        temp_file_path,
                        "--chunk-size",
                        str(chunk_size),
                    )

                    # Verify data was imported
                    self.assertEqual(Klant.objects.count(), 2)
                    self.assertEqual(ContainerLocation.objects.count(), 2)
                    self.assertEqual(Container.objects.count(), 2)
                    self.assertEqual(Lediging.objects.count(), 2)

                    # Verify specific data
                    klant = Klant.objects.get(bsn="123456782")
                    self.assertEqual(klant.naam, "Jan Jansen")

                    # Clean up for next test iteration
                    Lediging.objects.all().delete()
                    Container.objects.all().delete()
                    Klant.objects.all().delete()
                    ContainerLocation.objects.all().delete()

        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink()

    @patch("openafval.afval.management.commands.import_from_csv.import_from_file")
    def test_command_passes_chunk_size_argument(self, mock_import_from_file):
        call_command(
            "import_from_csv", "--file", "/path/to/file.csv", "--chunk-size", "10000"
        )

        mock_import_from_file.assert_called_once()
        call_args = mock_import_from_file.call_args
        # Should pass chunk_size as keyword argument
        self.assertEqual(call_args[1]["chunk_size"], 10000)
