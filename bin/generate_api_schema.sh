#!/bin/bash
#
# Generate the API schema from the code into the output file.
#
# Run this script from the root of the repository:
#
#   ./bin/generate_api_schema.sh [outfile]
#
# 'outfile' defaults to `src/openafval/api/openapi.yml`
#
# For multiple API specifications (different components or multiple major versions),
# take a look at the Open Zaak configuration.
#
set -eu -o pipefail

OUTFILE=${1:-src/openafval/api/openapi.yaml}

src/manage.py spectacular \
    --validate \
    --fail-on-warn \
    --lang=en \
    --file "$OUTFILE"
