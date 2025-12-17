#!/bin/bash
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-openafval-flower}"

exec celery flower --app openafval --workdir src
