from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class KlantProfiel:
    id: uuid.UUID
    bsn: str
    naam: str
    totaal_kosten: float


@dataclass
class ContainerProfiel:
    id: uuid.UUID
    public_container_id: str
    afval_type: str
    is_verzamelcontainer: bool
    heeft_sleutel: bool
    totaal_gewicht: float
    totaal_kosten: float


@dataclass
class ContainerLocatieProfiel:
    id: uuid.UUID
    adres: str
    totaal_gewicht: float
    totaal_kosten: float


@dataclass
class LedigingProfiel:
    id: uuid.UUID
    container_location: uuid.UUID
    klant: uuid.UUID
    container: uuid.UUID
    gewicht: float
    geleegd_op: datetime
    kosten: float


@dataclass
class AfvalProfiel:
    klant: KlantProfiel
    containers: list[ContainerProfiel]
    container_locaties: list[ContainerLocatieProfiel]
    ledigingen: list[LedigingProfiel]
