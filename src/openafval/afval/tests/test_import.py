import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from openafval.afval.models import Container, ContainerLocation, Klant, Lediging
from openafval.afval.services.import_services import import_from_csv_stream


class ImportFromCSVStreamTest(TestCase):
    def test_import_with_all_columns_populated(self):
        """Test importing CSV data with all columns properly populated."""
        csv_header = (
            "SUBJECTID;BSN;SUBJECTNAAM;OBJECTID;OBJECTADRES;CONTAINERID;"
            "SLEUTELNUMMER;VERZAMELCONTAINER_J_N;FRACTIEID;LEDIGINGID;"
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
            "SLEUTELNUMMER;VERZAMELCONTAINER_J_N;FRACTIEID;LEDIGINGID;"
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


class ImportFromCSVCommandTest(TestCase):
    def test_command_imports_csv_file_end_to_end(self):
        """Test that the command successfully imports a CSV file."""
        csv_header = (
            "SUBJECTID;BSN;SUBJECTNAAM;OBJECTID;OBJECTADRES;CONTAINERID;"
            "SLEUTELNUMMER;VERZAMELCONTAINER_J_N;FRACTIEID;LEDIGINGID;"
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as temp_file:
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
        call_command("import_from_csv", "/path/to/file.csv", "--chunk-size", "10000")

        mock_import_from_file.assert_called_once()
        call_args = mock_import_from_file.call_args
        # Should pass chunk_size as keyword argument
        self.assertEqual(call_args[1]["chunk_size"], 10000)

    @patch("openafval.afval.management.commands.import_from_csv.import_from_file")
    def test_command_with_local_path_calls_local_file_import(self, mock_import_from_file):
        call_command("import_from_csv", "/local/path/file.csv")

        mock_import_from_file.assert_called_once()
        call_args = mock_import_from_file.call_args

        # Should be called with the local path
        self.assertEqual(call_args[0][0], "/local/path/file.csv")

    @patch("openafval.afval.management.commands.import_from_csv.import_from_ftps_path")
    @patch.dict(os.environ, {"FTPS_PASSWORD": "testpass"})
    def test_command_with_ftps_url_calls_ftps_import_with_parsed_config(
        self, mock_import_from_ftps
    ):
        call_command(
            "import_from_csv",
            "ftps://example.com/data/file.csv",
            "--ftps-user",
            "testuser",
        )

        mock_import_from_ftps.assert_called_once()
        call_args = mock_import_from_ftps.call_args

        # Check FTPS config
        ftps_config = call_args[0][0]
        self.assertEqual(ftps_config["host"], "example.com")
        self.assertEqual(ftps_config["user"], "testuser")
        self.assertEqual(ftps_config["password"], "testpass")

        # Check remote path
        remote_path = call_args[0][1]
        self.assertEqual(remote_path, "data/file.csv")

    @patch("openafval.afval.management.commands.import_from_csv.import_from_ftps_path")
    @patch.dict(os.environ, {"FTPS_USER": "envuser", "FTPS_PASSWORD": "envpass"})
    def test_command_uses_environment_variables_for_ftps_credentials(self, mock_import_from_ftps):
        call_command(
            "import_from_csv",
            "ftps://example.com/data/file.csv",
        )

        mock_import_from_ftps.assert_called_once()
        call_args = mock_import_from_ftps.call_args

        # Should use credentials from environment variables
        ftps_config = call_args[0][0]
        self.assertEqual(ftps_config["user"], "envuser")
        self.assertEqual(ftps_config["password"], "envpass")

    @patch("openafval.afval.management.commands.import_from_csv.import_from_ftps_path")
    @patch.dict(os.environ, {"FTPS_USER": "envuser", "FTPS_PASSWORD": "envpass"})
    def test_command_line_user_arg_overrides_environment_variable(self, mock_import_from_ftps):
        call_command(
            "import_from_csv",
            "ftps://example.com/data/file.csv",
            "--ftps-user",
            "cliuser",
        )

        mock_import_from_ftps.assert_called_once()
        call_args = mock_import_from_ftps.call_args

        # Command line user argument should take precedence over env var
        ftps_config = call_args[0][0]
        self.assertEqual(ftps_config["user"], "cliuser")
        # Password should still come from environment
        self.assertEqual(ftps_config["password"], "envpass")

    @patch("openafval.afval.management.commands.import_from_csv.import_from_ftps_path")
    @patch("openafval.afval.management.commands.import_from_csv.getpass.getpass")
    @patch.dict(os.environ, {}, clear=True)
    def test_ftps_password_prompted_via_getpass_when_env_var_not_set(
        self, mock_getpass, mock_import_from_ftps
    ):
        mock_getpass.return_value = "prompted_password"

        call_command(
            "import_from_csv",
            "ftps://example.com/data/file.csv",
            "--ftps-user",
            "testuser",
        )

        mock_getpass.assert_called_once_with("Enter FTPS password: ")

        mock_import_from_ftps.assert_called_once()
        call_args = mock_import_from_ftps.call_args
        ftps_config = call_args[0][0]
        self.assertEqual(ftps_config["password"], "prompted_password")

    @patch("openafval.afval.management.commands.import_from_csv.import_from_ftps_path")
    @patch("openafval.afval.management.commands.import_from_csv.getpass.getpass")
    @patch.dict(os.environ, {"FTPS_PASSWORD": "envpass"}, clear=True)
    def test_ftps_password_not_prompted_when_env_var_is_set(
        self, mock_getpass, mock_import_from_ftps
    ):
        call_command(
            "import_from_csv",
            "ftps://example.com/data/file.csv",
            "--ftps-user",
            "testuser",
        )

        mock_getpass.assert_not_called()
        mock_import_from_ftps.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_ftps_url_raises_error_when_user_not_provided_via_arg_or_env(self):
        with self.assertRaises(CommandError) as cm:
            call_command(
                "import_from_csv",
                "ftps://example.com/data/file.csv",
            )

        self.assertEqual(
            str(cm.exception),
            "ftps:// URLs require --ftps-user (or FTPS_USER environment variable)",
        )

    @patch("openafval.afval.management.commands.import_from_csv.import_from_ftps_path")
    @patch.dict(os.environ, {"FTPS_USER": "envuser"}, clear=True)
    def test_ftps_user_read_from_env_var_when_arg_not_provided(self, mock_import_from_ftps):
        with patch(
            "openafval.afval.management.commands.import_from_csv.getpass.getpass"
        ) as mock_getpass:
            mock_getpass.return_value = "prompted_password"

            call_command(
                "import_from_csv",
                "ftps://example.com/data/file.csv",
            )

            mock_import_from_ftps.assert_called_once()
            call_args = mock_import_from_ftps.call_args
            ftps_config = call_args[0][0]
            self.assertEqual(ftps_config["user"], "envuser")
            self.assertEqual(ftps_config["password"], "prompted_password")

    @patch.dict(os.environ, {"FTPS_PASSWORD": "testpass"})
    def test_ftps_url_validation_errors(self):
        test_cases = [
            (
                "ftps:///data/file.csv",
                "Invalid FTPS URL: missing hostname",
                "missing hostname",
            ),
            (
                "ftps://user:pass@example.com/data/file.csv",
                "Credentials in URL are not supported. "
                "Use --ftps-user and FTPS_PASSWORD environment variable instead",
                "credentials in URL (user and password)",
            ),
            (
                "ftps://user@example.com/data/file.csv",
                "Credentials in URL are not supported. "
                "Use --ftps-user and FTPS_PASSWORD environment variable instead",
                "credentials in URL (username only)",
            ),
            (
                "ftps://example.com",
                "Invalid FTPS URL: missing file path",
                "missing path",
            ),
            (
                "ftps://example.com/",
                "Invalid FTPS URL: missing file path",
                "root path only",
            ),
        ]

        for url, expected_error, description in test_cases:
            with self.subTest(url=url, case=description):
                with self.assertRaises(CommandError) as cm:
                    call_command(
                        "import_from_csv",
                        url,
                        "--ftps-user",
                        "testuser",
                    )

                self.assertEqual(str(cm.exception), expected_error)
