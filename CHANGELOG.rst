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
