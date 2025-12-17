#!/bin/bash

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}

export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-openafval-scheduler}"

mkdir -p celerybeat

echo "Starting celery beat"
exec celery beat \
    --app openafval \
    -l $LOGLEVEL \
    --workdir src \
    -s ../celerybeat/beat
