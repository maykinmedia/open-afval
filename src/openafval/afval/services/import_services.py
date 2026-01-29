import logging
import os
import signal
import tempfile
import time
import zipfile
from ftplib import FTP_TLS
from pathlib import Path
from typing import IO, TypedDict, assert_never

from django.db import transaction

import pandas as pd

from openafval.afval.constants import AfvalTypeChoices
from openafval.afval.models import (
    Container,
    ContainerLocation,
    Klant,
    Lediging,
)

logger = logging.getLogger(__name__)

# FTPS download progress logging constants
BYTES_PER_MB = 1024 * 1024
LOG_PROGRESS_EVERY_MB = 100
FTP_CHUNK_SIZE = 8192  # Typical FTP chunk size in bytes


class FTPSConfig(TypedDict):
    """Configuration for FTPS connection."""

    host: str
    user: str
    password: str
    timeout: int  # in seconds


DTYPE_MAPPING = {
    "BSN": str,
    "CONTAINERID": str,
    "FRACTIEID": str,
    "GEWICHT_ONVERDEELD": float,
    "GEWICHT_VERDEELD": float,
    "LEDIGINGID": str,
    "OBJECTADRES": str,
    "OBJECTID": str,
    "SLEUTELNUMMER": str,
    "SUBJECTID": str,
    "SUBJECTNAAM": str,
    "VERZAMELCONTAINER_J_N": str,
}

DATE_COLUMNS: list[str] = []

DATETIME_COLUMNS = [
    "LEDIGINGSMOMENT",
]


def _csv_boolean(value: str) -> bool:
    # Handle missing/null values (pandas reads empty cells as NaN)
    if pd.isnull(value):
        return False

    match value:
        case "J":
            return True
        case "N":
            return False
        case _:  # pragma: no cover
            raise assert_never(value)


def _map_fractie_id_to_afval_type(fractie_id: str) -> str:
    """
    Map FRACTIEID from CSV (which contains waste type) to afval_type choices.
    """
    # Handle missing/null values (pandas reads empty cells as NaN/float)
    if pd.isnull(fractie_id) or not isinstance(fractie_id, str):
        return AfvalTypeChoices.RESTAFVAL.value

    fractie_id_lower = fractie_id.lower()

    if "gft" in fractie_id_lower or "groen" in fractie_id_lower:
        return AfvalTypeChoices.GFT.value
    elif "rest" in fractie_id_lower:
        return AfvalTypeChoices.RESTAFVAL.value
    else:
        # Default to restafval if unknown
        return AfvalTypeChoices.RESTAFVAL.value


@transaction.atomic
def import_from_csv_stream(stream: IO[str], chunk_size: int | None = None):
    start_time = time.time()

    if chunk_size is None:
        chunk_size = 50_000

    logger.info("Starting CSV import with chunk size: %s", f"{chunk_size:,}")

    # First pass: collect unique entities across all chunks
    unique_locations_dict: dict[str, str] = {}  # OBJECTID -> OBJECTADRES
    unique_klanten_dict: dict[str, tuple[str, str]] = {}  # SUBJECTID -> (BSN, NAAM)
    unique_containers_dict: dict[
        str, tuple[str, bool, bool]
    ] = {}  # CONTAINERID -> (afval_type, is_verzamelcontainer, heeft_sleutel)

    # Process CSV in chunks for first pass
    logger.info("First pass: collecting unique entities from CSV")
    chunk_iterator = pd.read_csv(
        stream,
        sep=";",
        dtype=DTYPE_MAPPING,
        parse_dates=DATE_COLUMNS + DATETIME_COLUMNS,
        chunksize=chunk_size,
    )

    chunk_count = 0
    total_rows_processed = 0
    for chunk_df in chunk_iterator:
        chunk_count += 1
        chunk_df = chunk_df.dropna(subset=["BSN", "LEDIGINGSMOMENT"])

        if len(chunk_df) == 0:
            logger.debug("Chunk %s: skipping (no valid rows after filtering)", chunk_count)
            continue

        total_rows_processed += len(chunk_df)
        logger.info(
            "Processing chunk %d: %s rows (total processed: %s)",
            chunk_count,
            f"{len(chunk_df):,}",
            f"{total_rows_processed:,}",
        )

        # Pre-process columns
        chunk_df["afval_type"] = chunk_df["FRACTIEID"].apply(_map_fractie_id_to_afval_type)
        chunk_df["is_verzamelcontainer"] = chunk_df["VERZAMELCONTAINER_J_N"].apply(_csv_boolean)
        chunk_df["heeft_sleutel"] = chunk_df["SLEUTELNUMMER"].notna() & (
            chunk_df["SLEUTELNUMMER"] != ""
        )

        # Collect unique entities from this chunk
        for row in chunk_df[["OBJECTID", "OBJECTADRES"]].drop_duplicates().itertuples(index=False):
            if row.OBJECTID not in unique_locations_dict:
                unique_locations_dict[row.OBJECTID] = row.OBJECTADRES

        for row in (
            chunk_df[["SUBJECTID", "BSN", "SUBJECTNAAM"]].drop_duplicates().itertuples(index=False)
        ):
            if row.SUBJECTID not in unique_klanten_dict:
                unique_klanten_dict[row.SUBJECTID] = (row.BSN, row.SUBJECTNAAM)

        for row in (
            chunk_df[["CONTAINERID", "afval_type", "is_verzamelcontainer", "heeft_sleutel"]]
            .drop_duplicates()
            .itertuples(index=False)
        ):
            if row.CONTAINERID not in unique_containers_dict:
                unique_containers_dict[row.CONTAINERID] = (
                    row.afval_type,
                    row.is_verzamelcontainer,
                    row.heeft_sleutel,
                )

    logger.info(
        "First pass complete: processed %d chunks, %s total rows",
        chunk_count,
        f"{total_rows_processed:,}",
    )
    logger.info(
        "Found %s unique locations, %s unique klanten, %s unique containers",
        f"{len(unique_locations_dict):,}",
        f"{len(unique_klanten_dict):,}",
        f"{len(unique_containers_dict):,}",
    )

    # Create Django model instances from collected unique entities
    container_locations_to_create = [
        ContainerLocation(adres=adres) for adres in unique_locations_dict.values()
    ]
    klanten_to_create = [Klant(bsn=bsn, naam=naam) for bsn, naam in unique_klanten_dict.values()]
    containers_to_create = [
        Container(
            afval_type=afval_type,
            is_verzamelcontainer=is_verzamel,
            heeft_sleutel=heeft_sleutel,
        )
        for afval_type, is_verzamel, heeft_sleutel in unique_containers_dict.values()
    ]

    # Purge all existing data before import
    # Delete in reverse FK order (Lediging references all others)
    logger.info("Deleting existing data")
    Lediging.objects.all().delete()
    Container.objects.all().delete()
    Klant.objects.all().delete()
    ContainerLocation.objects.all().delete()

    # Bulk create all unique objects
    logger.info("Creating %s container locations", f"{len(container_locations_to_create):,}")
    ContainerLocation.objects.bulk_create(container_locations_to_create, batch_size=1000)
    logger.info("Creating %s klanten", f"{len(klanten_to_create):,}")
    Klant.objects.bulk_create(klanten_to_create, batch_size=1000)
    logger.info("Creating %s containers", f"{len(containers_to_create):,}")
    Container.objects.bulk_create(containers_to_create, batch_size=1000)

    # Build mappings from external ID to created objects
    container_location_mapping = dict(
        zip(unique_locations_dict.keys(), container_locations_to_create, strict=True)
    )
    klant_mapping = dict(zip(unique_klanten_dict.keys(), klanten_to_create, strict=True))
    container_mapping = dict(zip(unique_containers_dict.keys(), containers_to_create, strict=True))

    # Free memory
    del (
        unique_locations_dict,
        unique_klanten_dict,
        unique_containers_dict,
        container_locations_to_create,
        klanten_to_create,
        containers_to_create,
    )

    # Second pass: create Lediging objects
    # Re-open the stream for second pass
    logger.info("Second pass: creating Lediging objects")
    stream.seek(0)
    chunk_iterator = pd.read_csv(
        stream,
        sep=";",
        dtype=DTYPE_MAPPING,
        parse_dates=DATE_COLUMNS + DATETIME_COLUMNS,
        chunksize=chunk_size,
    )

    chunk_count = 0
    total_ledigingen_created = 0
    for chunk_df in chunk_iterator:
        chunk_count += 1
        chunk_df = chunk_df.dropna(subset=["BSN", "LEDIGINGSMOMENT"])

        if len(chunk_df) == 0:
            logger.debug("Chunk %s: skipping (no valid rows after filtering)", chunk_count)
            continue

        logger.info(
            "Processing chunk %d: creating %s ledigingen",
            chunk_count,
            f"{len(chunk_df):,}",
        )

        # Convert timestamps
        chunk_df["geleegd_op_utc"] = pd.to_datetime(chunk_df["LEDIGINGSMOMENT"]).dt.tz_localize(
            "UTC"
        )

        # Create Lediging objects for this chunk
        ledigingen_batch = [
            Lediging(
                container_location=container_location_mapping[row.OBJECTID],
                klant=klant_mapping[row.SUBJECTID],
                container=container_mapping[row.CONTAINERID],
                gewicht=row.GEWICHT_VERDEELD,
                geleegd_op=row.geleegd_op_utc,
            )
            for row in chunk_df[
                [
                    "OBJECTID",
                    "SUBJECTID",
                    "CONTAINERID",
                    "GEWICHT_VERDEELD",
                    "geleegd_op_utc",
                ]
            ].itertuples(index=False)
        ]

        # Bulk create this chunk's ledigingen
        Lediging.objects.bulk_create(ledigingen_batch, batch_size=1000)
        total_ledigingen_created += len(ledigingen_batch)
        logger.info(
            "Chunk %d complete: %s ledigingen created (total: %s)",
            chunk_count,
            f"{len(ledigingen_batch):,}",
            f"{total_ledigingen_created:,}",
        )

        # Clear to free memory
        del ledigingen_batch

    end_time = time.time()
    duration_seconds = end_time - start_time
    duration_minutes = duration_seconds / 60
    duration_hours = duration_seconds / 3600

    logger.info(
        "Import complete: %s ledigingen created from %d chunks",
        f"{total_ledigingen_created:,}",
        chunk_count,
    )

    # Format duration based on length
    if duration_seconds < 60:
        logger.info("Total import duration: %.2f seconds", duration_seconds)
    elif duration_seconds < 3600:
        logger.info(
            "Total import duration: %.2f minutes (%.2f seconds)",
            duration_minutes,
            duration_seconds,
        )
    else:
        logger.info(
            "Total import duration: %.2f hours (%.2f minutes)",
            duration_hours,
            duration_minutes,
        )


def import_from_file(file: Path | str, chunk_size: int | None = None):
    file_path = Path(file) if isinstance(file, str) else file
    with file_path.open() as f:
        import_from_csv_stream(f, chunk_size=chunk_size)


def _secure_delete_file(file_path: str) -> None:
    """Securely delete a file by removing it and ensuring cleanup."""
    if os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.info("Securely deleted temporary file: %s", file_path)
        except Exception as e:
            logger.error("Failed to delete temporary file %s: %s", file_path, e)


def _extract_csv_from_zip(zip_path: str) -> tempfile._TemporaryFileWrapper:
    """Extract CSV file from ZIP archive to a temporary file.

    Args:
        zip_path: Path to ZIP archive

    Returns:
        NamedTemporaryFile containing the extracted CSV (caller must manage)

    Raises:
        ValueError: If archive contains no CSV files or multiple CSV files
    """
    with zipfile.ZipFile(zip_path) as zip_file:
        # Find first CSV file in the archive
        csv_files = [name for name in zip_file.namelist() if name.endswith(".csv")]

        if not csv_files:
            raise ValueError("No CSV files found in ZIP archive")

        if len(csv_files) > 1:
            raise ValueError(
                f"ZIP archive contains multiple CSV files: {csv_files}. "
                "Expected exactly one CSV file."
            )

        csv_filename = csv_files[0]
        logger.info("Found CSV file in archive: %s", csv_filename)

        # Extract CSV to temporary file for chunked processing
        csv_tmp = tempfile.NamedTemporaryFile(
            mode="w+b",
            delete=True,
            suffix=".csv",
            prefix="sensitive_extracted_",
        )
        os.chmod(csv_tmp.name, 0o600)
        logger.info("Created temporary CSV file: %s", csv_tmp.name)

        logger.info("Extracting CSV to temporary file")
        with zip_file.open(csv_filename) as csv_source:
            # Extract in 1MB chunks to avoid memory issues
            chunk_size = BYTES_PER_MB
            while True:
                chunk = csv_source.read(chunk_size)
                if not chunk:
                    break
                csv_tmp.write(chunk)

        csv_tmp.flush()
        return csv_tmp


def _setup_signal_handlers_for_file_cleanup(cleanup_paths: list[str]):
    """Setup signal handlers to clean up temporary files on interruption.

    Preserves existing signal handlers by chaining them.

    Args:
        cleanup_paths: List of file paths to clean up on signal

    Returns:
        Dictionary mapping signal numbers to their original handlers
    """
    original_handlers = {}

    def cleanup_handler(signum, frame):
        """Handle cleanup on signal, then call original handler."""
        logger.warning("Cleanup handler triggered by signal %s", signum)

        try:
            # Attempt to clean up temporary files
            for path in cleanup_paths:
                _secure_delete_file(path)
        except Exception:
            logger.exception("Error during secure file cleanup")
        finally:
            # Always handle original signal behavior, even if cleanup fails
            match original_handlers.get(signum):
                case signal.SIG_IGN:
                    # Signal was originally ignored, set back to ignore and don't terminate
                    signal.signal(signum, signal.SIG_IGN)
                case signal.SIG_DFL | None:
                    # Use default handler, set and re-raise to trigger default behavior
                    # (usually termination)
                    signal.signal(signum, signal.SIG_DFL)
                    os.kill(os.getpid(), signum)
                case handler:
                    # Custom handler existed, call it
                    handler(signum, frame)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        original_handlers[sig] = signal.signal(sig, cleanup_handler)

    return original_handlers


def _download_from_ftps(
    ftps_config: FTPSConfig,
    remote_path: str,
    local_file: IO[bytes],
) -> int:
    """Download a file from FTPS with progress logging.

    Args:
        ftps_config: FTPS connection configuration
        remote_path: Remote file path
        local_file: Local file object to write to (binary mode)

    Returns:
        Number of bytes downloaded
    """
    logger.info("Downloading from FTPS: %s", remote_path)
    bytes_downloaded = 0

    def write_with_progress(data):
        nonlocal bytes_downloaded
        local_file.write(data)
        bytes_downloaded += len(data)

        # Log progress periodically
        if bytes_downloaded % (LOG_PROGRESS_EVERY_MB * BYTES_PER_MB) < FTP_CHUNK_SIZE:
            mb_downloaded = bytes_downloaded / BYTES_PER_MB
            logger.info("Downloaded %.1f MB...", mb_downloaded)

    with FTP_TLS(ftps_config["host"], timeout=ftps_config["timeout"]) as ftps:
        ftps.login(ftps_config["user"], ftps_config["password"])
        ftps.prot_p()  # Enable encryption

        ftps.retrbinary(f"RETR {remote_path}", write_with_progress)

        mb_total = bytes_downloaded / BYTES_PER_MB
        logger.info("Download complete: %.1f MB", mb_total)

    return bytes_downloaded


def import_from_ftps_path(ftps_config: FTPSConfig, remote_path: str, chunk_size: int | None = None):
    """Download and process a CSV file (or ZIP containing CSV) from FTPS.

    The file is downloaded to a secure temporary location with restricted
    permissions and automatically deleted even if the process is interrupted.
    If the file is a ZIP archive, it must contain exactly one CSV file, which
    will be extracted and processed.

    Args:
        ftps_config: FTPS connection configuration with 'host', 'user', 'password'
        remote_path: Remote path to the CSV or ZIP file
        chunk_size: Number of rows to process per chunk (default: 50,000)

    Raises:
        ValueError: If ZIP contains no CSV files or multiple CSV files
    """
    is_zip = remote_path.lower().endswith(".zip")
    suffix = ".zip" if is_zip else ".csv"

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=True,
        suffix=suffix,
        prefix="sensitive_",
    ) as downloaded_file:
        # Setup secure permissions and signal handlers
        os.chmod(downloaded_file.name, 0o600)
        logger.info("Created temporary file: %s", downloaded_file.name)

        cleanup_paths = [downloaded_file.name]
        original_handlers = _setup_signal_handlers_for_file_cleanup(cleanup_paths)

        try:
            # Download file
            bytes_downloaded = _download_from_ftps(ftps_config, remote_path, downloaded_file)
            downloaded_file.flush()  # Ensure all data is written to disk

            # Verify file was downloaded
            file_size = os.path.getsize(downloaded_file.name)
            logger.info(
                "Downloaded file size: %d bytes (reported: %d)",
                file_size,
                bytes_downloaded,
            )

            # Get CSV file path (either direct or extracted from ZIP)
            if is_zip:
                logger.info("Extracting ZIP archive from: %s", downloaded_file.name)
                with _extract_csv_from_zip(downloaded_file.name) as csv_file:
                    cleanup_paths.append(csv_file.name)
                    logger.info("Processing extracted CSV")
                    with open(csv_file.name, encoding="utf-8") as text_file:
                        import_from_csv_stream(text_file, chunk_size=chunk_size)
            else:
                logger.info("Processing CSV file")
                with open(downloaded_file.name, encoding="utf-8") as text_file:
                    import_from_csv_stream(text_file, chunk_size=chunk_size)
        finally:
            # Restore original signal handlers
            for sig, handler in original_handlers.items():
                signal.signal(sig, handler)
