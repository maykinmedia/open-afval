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
