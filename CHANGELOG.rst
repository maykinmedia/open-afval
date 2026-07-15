0.8.0 (2026-07-15)
==================

New features
============

* [:pr:`48`]: Add ``med`` (medisch afval) as a new ``AfvalTypeChoices`` value, mapped
  from the CSV import's ``FRACTIE_ID`` column.

Bug fixes
=========

* [:pr:`42`]: Fix drift between the CSV import's expected column names and the source
  file (``CONTAINERID``, ``FRACTIEID``, ``LEDIGINGID``, ``OBJECTID``, and
  ``SUBJECTID`` renamed to ``CONTAINER_ID``, ``FRACTIE_ID``, ``LEDIGING_ID``,
  ``OBJECT_ID``, and ``SUBJECT_ID`` respectively), which broke CSV imports.

Maintenance
===========

* [:pr:`46`]: Bump Python (idna, soupsieve, pyjwt, cryptography) and npm (fast-uri,
  minimatch, tmp, serialize-javascript, svgo, ws, and others) dependencies
  (Dependabot).
* [:pr:`47`]: Disable OAS linting workflow.


0.7.0 (2026-07-01)
==================

New features
============

* [:pr:`38`]: Add ``publicContainerId`` to the ``AfvalProfiel`` API response, sourced
  from the CSV import's ``CONTAINERID`` column.

Bug fixes
=========

* [:pr:`40`]: Use ``DecimalField`` for ``Lediging.kosten`` instead of a float, avoiding
  floating-point rounding errors in cost aggregation.
* [:pr:`40`]: Warn instead of silently mapping to restafval when the CSV import
  encounters an unknown ``FRACTIEID``.
* [:pr:`40`]: Drop CSV rows missing ``CONTAINERID``, ``OBJECTID``, or ``SUBJECTID``
  before building import mappings, fixing a ``KeyError`` during import.

Maintenance
===========

* [:pr:`38`]: Pin all GitHub Actions to SHA digests and add zizmor for workflow
  security scanning.
* [:pr:`39`]: Bump Django, urllib3, protobuf, GitPython, and Node.js dependencies.


0.6.1 (2026-06-29)
==================

Bug fixes
=========

* [:pr:`36`]: Move ``totaalKosten`` from the top-level ``AfvalProfiel`` response into
  the ``klant`` resource.


0.6.0 (2026-06-29)
==================

Bug fixes
=========

* [:pr:`34`]: Expose ``totaalKosten`` (sum of lediging costs) at the ``AfvalProfiel``
  level, alongside the existing per-container and per-location totals.


0.5.0 (2026-06-25)
==================

New features
============

* [:pr:`30`]: Add ``kosten`` field to the ``Lediging`` model, serializer, admin, and CSV
  import (source column: ``TOTAALKOSTEN_LEDIGING``).
* [:pr:`31`]: Expose total ledigingen cost aggregated per klant, container location, and
  container.

Bug fixes
=========

* [:pr:`27`]: Require SSL session reuse on the FTPS data channel to fix error 522 on
  servers that enforce RFC 4217 session resumption.

Maintenance
===========

* [:pr:`32`]: Add pytest configuration to ``pyproject.toml``.


0.4.0 (2026-06-08)
==================

Bug fixes
=========

* Upgrade ``django-setup-configuration`` to 0.12.0 and configure the required
  setup steps (OIDC and user configuration). Without this, the setup
  configuration management command had no steps to execute, making it
  effectively unusable.


0.3.0 (2026-02-26)
==================

New features
============

* [:gh:`17`, :pr:`18`]: Fetch diftar CSV directly from FTPS server.
* [:gh:`9`]: Implement filters for afval resources (date range, waste type, and
  address for ContainerLocation objects).
* [:gh:`2218`]: Expose CSV import functionality to superusers in admin interface.

Bug fixes
=========

* [:gh:`19`, :pr:`21`]: Use correct mapping for waste type when importing from CSV
  (CONTAINERSOORT replaced with FRACTIEID).


0.2.0 (2026-02-02)
==================

New features
============

- Updated API endpoints and serializers for new model structure
- Switched to Pandas operations for importing data from CSV

Maintenance
============

- Removed Pyright type checking from CI
- Changed ruff line length to 100


0.1.0
=====

*<month, day year>*

* Initial release.
