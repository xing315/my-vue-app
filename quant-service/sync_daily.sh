#!/bin/sh
set -eu
cd "$(dirname "$0")"
weekday=$(date +%u)
if [ "$weekday" -gt 5 ]; then
  echo "$(date '+%F %T') weekend: skip quant sync"
  exit 0
fi
mkdir -p data/logs
echo "$(date '+%F %T') quant sync started"
QUANT_REQUIRE_SUPABASE_PUBLISH=1 ./run_pipeline.sh
echo "$(date '+%F %T') quant sync completed"
