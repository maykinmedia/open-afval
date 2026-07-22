from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone
from django.utils.formats import date_format, number_format

from .constants import AfvalTypeChoices
from .profiel import AfvalProfiel

_ADDRESS_RE = re.compile(r"^(.+?)\s*\[([0-9]{4})([A-Z]{2})\s+(.+?)\]$")


def _format_number(value: int | float | Decimal, decimal_places: int | None = None) -> str:
    if decimal_places is None:
        decimal_places = 0 if isinstance(value, int) else 1
    return number_format(value, decimal_pos=decimal_places, force_grouping=False)


def _get_container_type_label(afval_type: str) -> str:
    try:
        return AfvalTypeChoices(afval_type).label
    except ValueError:
        return afval_type


def _format_address(adres: str) -> str:
    """
    Format address from raw stored format to display format.

    Raw format: "Dorpsstraat 12 [1234AB AMSTERDAM]"
    Display format: "Dorpsstraat 12, 1234 AB, Amsterdam"
    """
    address = adres.replace("\n", " ").replace("\r", " ")
    address = re.sub(r"\s+", " ", address).strip()

    match = _ADDRESS_RE.match(address)
    if not match:
        return address

    street, postcode_digits, postcode_letters, city = match.groups()
    return f"{street.strip()}, {postcode_digits} {postcode_letters}, {city.strip().title()}"


def format_afval_profiel(profiel: AfvalProfiel) -> list[dict]:
    """
    Group the flat AfvalProfiel into container location -> containers -> ledigingen,
    formatted for display (mirrors open-inwoner's mijn_afval presentation).
    """
    containers_by_id = {container.id: container for container in profiel.containers}

    ledigingen_by_container: dict = defaultdict(list)
    for lediging in profiel.ledigingen:
        if lediging.container not in containers_by_id:
            continue
        ledigingen_by_container[lediging.container].append(lediging)

    result = []
    for locatie in profiel.container_locaties:
        containers_data = []

        for container_id, ledigingen in ledigingen_by_container.items():
            locatie_ledigingen = [
                lediging for lediging in ledigingen if lediging.container_location == locatie.id
            ]
            if not locatie_ledigingen:
                continue

            container = containers_by_id[container_id]
            rows = []
            for lediging in locatie_ledigingen:
                geleegd_op = timezone.localtime(lediging.geleegd_op)
                dag = date_format(geleegd_op, "D")
                rows.append(
                    {
                        "datum": f"{dag} {geleegd_op.strftime('%d-%m-%Y')}",
                        "tijd": geleegd_op.strftime("%H:%M"),
                        "gewicht": _format_number(lediging.gewicht),
                        "kosten": _format_number(lediging.kosten, decimal_places=2),
                    }
                )

            containers_data.append(
                {
                    "public_container_id": container.public_container_id,
                    "type_label": _get_container_type_label(container.afval_type),
                    "totaal_gewicht": _format_number(container.totaal_gewicht),
                    "totaal_kosten": _format_number(container.totaal_kosten, decimal_places=2),
                    "rows": rows,
                }
            )

        result.append(
            {
                "adres": _format_address(locatie.adres),
                "totaal_gewicht": _format_number(locatie.totaal_gewicht),
                "containers": containers_data,
            }
        )

    return result
