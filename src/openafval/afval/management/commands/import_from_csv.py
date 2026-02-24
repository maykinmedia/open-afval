import getpass
import os
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError

from openafval.afval.services.exceptions import CSVImportError
from openafval.afval.services.import_services import (
    FTPSConfig,
    import_from_file,
    import_from_ftps_path,
)


class Command(BaseCommand):
    help = "Import data for 'Mijn Afval' from CSV file (local or FTPS)."

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            help="Path to CSV file (local path or ftps://host/path/to/file.csv)",
        )
        parser.add_argument(
            "--ftps-user",
            type=str,
            help=(
                "FTPS username (required for ftps:// URLs, can use FTPS_USER env var). "
                "Password will be prompted interactively or can be set via FTPS_PASSWORD env var"
            ),
            required=False,
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            help="Number of rows to process from the CSV in a single chunk",
            required=False,
        )
        parser.add_argument(
            "--ftps-timeout",
            type=int,
            default=60,
            help="FTPS connection timeout in seconds (default: 60)",
            required=False,
        )

    def handle(self, **options):
        source: str = options["source"]
        ftps_user: str | None = options["ftps_user"] or os.environ.get("FTPS_USER")
        ftps_password: str | None = os.environ.get("FTPS_PASSWORD")
        ftps_timeout: int = options["ftps_timeout"]
        chunk_size: int | None = options["chunk_size"]

        try:
            # Check if source is an FTPS URL
            if source.startswith("ftps://"):
                # Validate FTPS credentials are provided
                if not ftps_user:
                    raise CommandError(
                        "ftps:// URLs require --ftps-user (or FTPS_USER environment variable)"
                    )

                # Prompt for password if not provided via environment variable
                if not ftps_password:
                    self.stdout.write(
                        "FTPS password not found in FTPS_PASSWORD environment variable."
                    )
                    ftps_password = getpass.getpass("Enter FTPS password: ")

                # Parse the FTPS URL
                parsed = urlparse(source)

                # Validate URL structure
                if not parsed.netloc:
                    raise CommandError("Invalid FTPS URL: missing hostname")
                if parsed.username or parsed.password:
                    raise CommandError(
                        "Credentials in URL are not supported. "
                        "Use --ftps-user and FTPS_PASSWORD environment variable instead"
                    )
                if not parsed.path or parsed.path == "/":
                    raise CommandError("Invalid FTPS URL: missing file path")

                # Build FTPS config
                ftps_config: FTPSConfig = {
                    "host": parsed.netloc,
                    "user": ftps_user,
                    "password": ftps_password,
                    "timeout": ftps_timeout,
                }

                # Extract the remote path (remove leading /)
                remote_path = parsed.path.lstrip("/")

                # Import from FTPS
                self.stdout.write(f"Importing from FTPS: {source}")
                import_from_ftps_path(ftps_config, remote_path, chunk_size=chunk_size)
            else:
                # Import from local file
                self.stdout.write(f"Importing from local file: {source}")
                import_from_file(source, chunk_size=chunk_size)

            self.stdout.write(self.style.SUCCESS("Import completed successfully"))

        except CSVImportError as exc:
            raise CommandError(exc.message) from exc
