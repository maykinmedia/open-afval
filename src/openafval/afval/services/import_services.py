from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO, TypedDict, assert_never, cast

from django.db import transaction

import pandas as pd

from openafval.afval.constants import AfvalTypeChoices
from openafval.afval.models import (
    Container,
    ContainerLocation,
    Klant,
    Lediging,
)

DTYPE_MAPPING = {
    "SUBJECTID": str,
    "BSN": str,
    "SUBJECTNAAM": str,
    "OBJECTID": str,
    "OBJECTADRES": str,
    "CONTAINERID": str,
    "SLEUTELNUMMER": str,
    "VERZAMELCONTAINER_J_N": str,
    "CONTAINERSOORT": str,
    "LEDIGINGID": str,
    "GEWICHT_ONVERDEELD": float,
    "GEWICHT_VERDEELD": float,
}

DATE_COLUMNS: list[str] = []

DATETIME_COLUMNS = [
    "LEDIGINGSMOMENT",
]


@dataclass(frozen=True)
class RowType:
    SUBJECTID: str
    BSN: str
    SUBJECTNAAM: str
    OBJECTID: str
    OBJECTADRES: str
    CONTAINERID: str
    SLEUTELNUMMER: str
    VERZAMELCONTAINER_J_N: str
    CONTAINERSOORT: str
    LEDIGINGID: str
    GEWICHT_ONVERDEELD: float
    GEWICHT_VERDEELD: float
    LEDIGINGSMOMENT: pd.Timestamp


class LedigingData(TypedDict):
    objectid: str
    subjectid: str
    containerid: str
    gewicht: float
    geleegd_op: datetime | None


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


def _map_containersoort_to_afval_type(containersoort: str) -> str:
    """
    Map CONTAINERSOORT from CSV to afval_type choices.
    """
    # Handle missing/null values (pandas reads empty cells as NaN/float)
    if pd.isnull(containersoort) or not isinstance(containersoort, str):
        return AfvalTypeChoices.RESTAFVAL.value

    containersoort_lower = containersoort.lower()

    if "gft" in containersoort_lower or "groen" in containersoort_lower:
        return AfvalTypeChoices.GFT.value
    elif "rest" in containersoort_lower:
        return AfvalTypeChoices.RESTAFVAL.value
    else:
        # Default to restafval if unknown
        return AfvalTypeChoices.RESTAFVAL.value


def build_dataframe_from_csv_stream(stream: IO[str]) -> pd.DataFrame:
    dataframe = pd.read_csv(
        stream,
        sep=";",
        dtype=DTYPE_MAPPING,
        parse_dates=DATE_COLUMNS + DATETIME_COLUMNS,
        low_memory=False,
    )
    return dataframe.reset_index()


@transaction.atomic
def import_from_csv_stream(stream: IO[str]):
    # Purge all existing data before import
    # Delete in reverse FK order (Lediging references all others)
    Lediging.objects.all().delete()
    Container.objects.all().delete()
    Klant.objects.all().delete()
    ContainerLocation.objects.all().delete()

    df = build_dataframe_from_csv_stream(stream)

    # Filter out rows with empty/null BSN or LEDIGINGSMOMENT values
    df = df[(df["BSN"].notna()) & (df["LEDIGINGSMOMENT"].notna())]

    # First pass: collect unique objects to create
    container_locations_to_create: dict[str, ContainerLocation] = {}
    klanten_to_create: dict[str, Klant] = {}
    containers_to_create: dict[str, Container] = {}
    ledigingen_data: list[LedigingData] = []

    for row_tuple in df.itertuples(index=False):
        row = cast(RowType, row_tuple)

        # Collect unique ContainerLocations
        if row.OBJECTID not in container_locations_to_create:
            container_locations_to_create[row.OBJECTID] = ContainerLocation(
                adres=row.OBJECTADRES
            )

        # Collect unique Klanten
        if row.SUBJECTID not in klanten_to_create:
            klanten_to_create[row.SUBJECTID] = Klant(
                bsn=row.BSN,
                naam=row.SUBJECTNAAM,
            )

        # Collect unique Containers
        if row.CONTAINERID not in containers_to_create:
            afval_type = _map_containersoort_to_afval_type(row.CONTAINERSOORT)
            containers_to_create[row.CONTAINERID] = Container(
                afval_type=afval_type,
                is_verzamelcontainer=_csv_boolean(row.VERZAMELCONTAINER_J_N),
                heeft_sleutel=bool(row.SLEUTELNUMMER)
                if not pd.isnull(row.SLEUTELNUMMER)
                else False,
            )

        # Store lediging data for later (need FK references first)
        gewicht = row.GEWICHT_VERDEELD
        ledigingen_data.append(
            {
                "objectid": row.OBJECTID,
                "subjectid": row.SUBJECTID,
                "containerid": row.CONTAINERID,
                "gewicht": gewicht,
                "geleegd_op": (
                    None
                    if pd.isnull(row.LEDIGINGSMOMENT)
                    else pd.to_datetime(row.LEDIGINGSMOMENT).tz_localize("UTC")
                ),
            }
        )

    # Bulk create all unique objects
    ContainerLocation.objects.bulk_create(
        container_locations_to_create.values(), batch_size=1000
    )
    Klant.objects.bulk_create(klanten_to_create.values(), batch_size=1000)
    Container.objects.bulk_create(containers_to_create.values(), batch_size=1000)

    # Build mappings from external ID to created objects
    # (bulk_create updates the objects with their DB IDs)
    container_location_mapping: dict[str, ContainerLocation] = {
        obj_id: obj for obj_id, obj in container_locations_to_create.items()
    }
    klant_mapping: dict[str, Klant] = {
        subj_id: obj for subj_id, obj in klanten_to_create.items()
    }
    container_mapping: dict[str, Container] = {
        cont_id: obj for cont_id, obj in containers_to_create.items()
    }

    # Create Lediging objects with proper FK references
    ledigingen_to_create = [
        Lediging(
            container_location=container_location_mapping[data["objectid"]],
            klant=klant_mapping[data["subjectid"]],
            container=container_mapping[data["containerid"]],
            gewicht=data["gewicht"],
            geleegd_op=data["geleegd_op"],
        )
        for data in ledigingen_data
    ]

    # Bulk create all ledigingen
    Lediging.objects.bulk_create(ledigingen_to_create, batch_size=1000)


def import_from_file(file: Path | str):
    file_path = Path(file) if isinstance(file, str) else file
    with file_path.open() as f:
        import_from_csv_stream(f)
