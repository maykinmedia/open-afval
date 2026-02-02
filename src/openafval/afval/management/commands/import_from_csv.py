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
            help="FTPS username (required for ftps:// URLs, can use FTPS_USER env var)",
            required=False,
        )
        parser.add_argument(
            "--ftps-password",
            type=str,
            help=("FTPS password (required for ftps:// URLs, can use FTPS_PASSWORD env var)"),
            required=False,
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            help="Number of rows to process from the CSV in a single chunk",
            required=False,
        )

    def handle(self, *args, **options):
        source: str = options["source"]
        ftps_user: str | None = options["ftps_user"] or os.environ.get("FTPS_USER")
        ftps_password: str | None = options["ftps_password"] or os.environ.get("FTPS_PASSWORD")
        chunk_size: int | None = options["chunk_size"]

        try:
            # Check if source is an FTPS URL
            if source.startswith("ftps://"):
                # Validate FTPS credentials are provided
                if not ftps_user or not ftps_password:
                    raise CommandError(
                        "ftps:// URLs require --ftps-user and --ftps-password "
                        "(or FTPS_USER and FTPS_PASSWORD environment variables)"
                    )

                # Parse the FTPS URL
                parsed = urlparse(source)

                # Build FTPS config
                ftps_config: FTPSConfig = {
                    "host": parsed.netloc,
                    "user": ftps_user,
                    "password": ftps_password,
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
