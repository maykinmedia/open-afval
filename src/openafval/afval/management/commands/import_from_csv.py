from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from openafval.afval.services.exceptions import CSVImportError
from openafval.afval.services.import_services import import_from_file


class Command(BaseCommand):
    help = "Import data for 'Mijn Afval' from CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            action="store",
            help="Path to CSV file for importing",
            required=True,
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            help="Number of rows to process from the CSV in a single chunk",
            required=False,
        )

    def handle(self, *args, **options):
        file: Path = options["file"]
        chunk_size: int = options["chunk_size"]

        try:
            import_from_file(file, chunk_size=chunk_size)
        except CSVImportError as exc:
            raise CommandError(exc.message) from exc
