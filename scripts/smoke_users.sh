#!/usr/bin/env bash
# Smoke test: proves the explicit `send-user` / `send-advance-user` commands
# drive the Avro Users link end-to-end against a running docker compose stack
# (explicit command -> faust.codecs registration -> topic -> consumer log).
#
# Prereqs:
#   1. docker compose stack is up, e.g.:   docker-compose up -d
#      (zookeeper + kafka + schema-registry + faust-project)
#   2. the faust-project image has the package installed (`pip install -e .`,
#      which the Dockerfile already does).
#
# Run from the repo root:
#   bash scripts/smoke_users.sh
#
# Expected output: every step prints an "OK:" line and the script ends with
# "SMOKE PASS". On any failure it prints "FAIL:" and exits non-zero.
set -euo pipefail

if command -v docker-compose >/dev/null 2>&1; then
  DC=docker-compose
else
  DC="docker compose"
fi

SERVICE=faust-project
APP="faust -A example.app"
EXEC="$DC exec -T -e SIMPLE_SETTINGS=settings $SERVICE $APP"

echo "==[1/4] send a simple user via the explicit command entry =="
$EXEC send-user '{"first_name": "Smoke", "last_name": "Simple"}' \
  | grep -E "OK: simple user sent to topic 'avro_users'" \
  || { echo "FAIL: simple user command did not report OK"; exit 1; }

echo "==[2/4] send an advance user via the explicit command entry =="
$EXEC send-advance-user \
  '{"first_name": "Smoke", "last_name": "Advance", "age": 7}' \
  | grep -E "OK: advance user sent to topic 'advance_avro_users'" \
  || { echo "FAIL: advance user command did not report OK"; exit 1; }

echo "==[3/4] the running worker must have consumed both events =="
# 10s gives the first send enough time to register its Avro schema with the
# schema-registry and for the worker to poll/deliver the events.
sleep 10
$DC logs --no-color $SERVICE 2>&1 \
  | grep -E "First Name: Smoke, last name Simple" \
  || { echo "FAIL: simple user event not seen in consumer logs"; exit 1; }
$DC logs --no-color $SERVICE 2>&1 \
  | grep -E "First Name: Smoke, last name Advance, age 7" \
  || { echo "FAIL: advance user event not seen in consumer logs"; exit 1; }
echo "OK: both events reached their consumer agents"

echo "==[4/4] the command entry rejects invalid JSON with a clear message =="
if $EXEC send-user '{not json' 2>&1 | grep -q "Invalid JSON payload"; then
  echo "OK: invalid JSON rejected"
else
  echo "FAIL: invalid JSON was not rejected by the command entry"; exit 1
fi

echo "SMOKE PASS: Users explicit-command -> Avro codec -> topic -> consumer link works"
