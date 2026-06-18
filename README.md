# Faust-Docker-Compose

[![Build Status](https://travis-ci.org/marcosschroh/faust-docker-compose-example.svg?branch=master)](https://travis-ci.org/marcosschroh/faust-docker-compose-example)
[![License](https://img.shields.io/github/license/marcosschroh/faust-docker-compose-example.svg?logo=MIT)](https://github.com/marcosschroh/faust-docker-compose-example/blob/master/LICENSE)

An example to show how to include a `faust` project as a service using `docker compose`, with [Kafka](https://kafka.apache.org/), [Zookeeper](https://zookeeper.apache.org/) and [Schema Registry](https://docs.confluent.io/current/schema-registry/docs/index.html)

Notice that everything runs using `docker-compose`, including the faust example application. For
local development is preferable to run the `kafka` cluster separate from the `faust app`.

If you want to generate a `faust` project from scratch, please use the [cookiecutter-faust](https://github.com/marcosschroh/cookiecutter-faust)

Read more about Faust here: https://github.com/robinhood/faust

## Project

The project skeleton is defined as a medium/large project according to [faust layout](https://faust.readthedocs.io/en/latest/userguide/application.html#projects-and-directory-layout)

The `setup.py` has the entrypoint to resolve the [entrypoint problem](https://faust.readthedocs.io/en/latest/userguide/application.html#problem-entrypoint)

## Applications

* *Page Views*: This application corresponds to [Tutorial: Count page views](https://faust.readthedocs.io/en/latest/playbooks/pageviews.html)
* *Leader Election*: This application corresponds to [Tutorial: Leader Election](https://faust.readthedocs.io/en/latest/playbooks/leaderelection.html)
* *Users*: This is a custom application to demostrate how to integrate `Faust` with `Avro Schema`.

## Faust Project Dockerfile

The `Dockerfile` is based on  `python:3.7-slim`. The most important here is that the [`entrypoint`]() will wait for `kafka` too be ready and after that execute the script [`run.sh`]()

## Docker compose

`docker-compose.yaml` includes `zookeepeer`, `kafka` and `schema-registry` based on `confluent-inc`.
For more information you can go to [confluentinc](https://docs.confluent.io/current/installation/docker/docs/index.html) and see the docker compose example [here](https://github.com/confluentinc/cp-docker-images/blob/master/examples/cp-all-in-one/docker-compose.yml#L23-L48)

Useful ENVIRONMENT variables that you may change:

|Variable| description  | example |
|--------|--------------|---------|
| WORKER | Entrypoint in setup.py | `example`|
| WORKER_PORT | Worker port | `6066` |
| KAFKA_BOOSTRAP_SERVER | Kafka servers | `kafka://kafka:9092` |
| KAFKA_BOOSTRAP_SERVER_NAME | Kafka server name| `kafka` |
| KAFKA_BOOSTRAP_SERVER_PORT | Kafka server port | `9092` |
| SCHEMA_REGISTRY_SERVER | Schema registry server name | `schema-registry` |
| SCHEMA_REGISTRY_SERVER_PORT | Schema registry server port | `8081` |
| SCHEMA_REGISTRY_URL | Schema Registry Server url | `http://schema-registry:8081` |

## Commands

* Start application: `make run-dev`. This command starts the Kafka cluster, Schema Registry and all Faust applications (Page Views, Leader Election, Users)
* Stop and remove containers: `make clean`
* List topics: `make list-topics`
* Run tests (services must already be running): `make test`

### Send events

**Page Views** (JSON, built-in `faust send`):
```bash
make send-page-view-event payload='{"id": "foo", "user": "bar"}'
```

**Simple User** (Avro, topic `avro_users`, fields: `first_name`, `last_name`):
```bash
make send-user-event payload='{"first_name": "Alice", "last_name": "Smith"}'
```

**Advance User** (Avro, topic `advance_avro_users`, fields: `first_name`, `last_name`, `age`):
```bash
make send-advance-user-event payload='{"first_name": "Bob", "last_name": "Jones", "age": 30}'
```

### Create topics explicitly (optional — Faust auto-creates them)
```bash
make create-page-view-topic
make create-avro-users-topic
make create-advance-avro-users-topic
# or
make create-all-user-topics
```

## Avro Schemas, Custom Codecs and Serializers

Because we want to be sure that the messages we encode are valid we use [Avro Schemas](https://docs.oracle.com/database/nosql-12.1.3.1/GettingStartedGuide/avroschemas.html).
Avro is used to define the data schema for a record's value. This schema describes the fields allowed in the value, along with their data types.

The `Users` example provides **two** separate Avro-based paths — a "simple user" and an "advance user" — each with its own topic, serializer and schema. The mapping is centralized in `example/codecs/avro.py` (see `USER_TOPIC_CONFIG`):

| Path | Kafka Topic | Model | Serializer Name | Schema Subject | Required Fields |
|------|-------------|-------|-----------------|----------------|-----------------|
| Simple User | `avro_users` | `UserModel` | `avro_users` | `users` | `first_name`, `last_name` |
| Advance User | `advance_avro_users` | `AdvanceUserModel` | `avro_advance_users` | `advance_users` | `first_name`, `last_name`, `age` |

The simple-user Avro schema is:

```json
{
    "type": "record",
    "namespace": "com.example",
    "name": "AvroUsers",
    "fields": [
        {"name": "first_name", "type": "string"},
        {"name": "last_name", "type": "string"}
    ]
}
```

The advance-user schema is derived automatically from `AdvanceUserModel` via `dataclasses-avroschema` and adds the `age` (int) field.

In order to use `avro schemas` with `Faust` we need to define a custom codec, a custom serializer and be able to talk with the `schema-registry`.
The codecs `avro_users` and `avro_advance_users` are registered via the setup.py entry-points (`faust.codecs` group). The `FaustSerializer` from [python-schema-registry-client](https://github.com/marcosschroh/python-schema-registry-client) handles encoding and decoding against the Schema Registry.

Integrating the Faust model with the Avro serializer is done by pointing the `serializer` class kwarg at the registered codec name:

```python
# users.models

class UserModel(faust.Record, serializer='avro_users'):
    first_name: str
    last_name: str
```

### Explicit send entrypoints

Sending is **not** limited to the built-in 5-second timers. Two dedicated Faust CLI commands are defined as `AppCommand` classes in `example/users/cli.py`:

- `faust -A example.app send-user '<json>'`  — validates and sends a simple user to `avro_users`
- `faust -A example.app send-advance-user '<json>'`  — validates and sends an advance user to `advance_avro_users`

> Note: click registers faust commands with dashes, so the invocable names are `send-user` / `send-advance-user` (not `send_user`). The `make send-user-event` / `make send-advance-user-event` targets wrap these for you.

**They are available on the real CLI path with no extra imports.** `example/app.py` imports `example.users.cli` at the end of the module (after `app` is defined), so when `faust -A example.app <cmd>` runs faust's `find_app` → `prepare_app` (which imports `example.app`), the `send-user` / `send-advance-user` subcommands register into the faust `cli` group at import time. Venusian autodiscovery (`autodiscover=True`, `origin='example'`) stays enabled as Faust's normal mechanism; the explicit import is a belt-and-suspenders guarantee so the commands register even on interpreters where venusian's package walk is unavailable.

Both commands run **payload validation before sending**:

- Missing required fields → `click.ClickException` (lists missing + required)
- Extra/unexpected fields → `click.ClickException` (lists unexpected + allowed)
- Wrong value types (e.g. `age` as a string, `first_name` as int) → `click.ClickException`
- Invalid JSON → `click.BadParameter` (clear parse error)

Validation logic lives in `example/codecs/avro.py::validate_user_payload` and is also exposed as `UserModel.from_payload` / `AdvanceUserModel.from_payload` for programmatic use.

The two `@app.timer` tasks (`publish_users`, `advance_publish_users`) continue to publish hardcoded samples every 5 seconds, but now delegate to the same `send_simple_user` / `send_advance_user` helpers used by the CLI commands — so the timer and manual paths share validation, serializer selection and topic routing.

### Verification of the Users link

The Users link is verified at three levels, all repeatable from the repo:

1. **Command registration, real path (unit, `tests/test_users_cli.py::TestCommandRegistrationViaAppImport`)** — spawns a *clean* interpreter that imports **only** `example.app` (not `example.users.cli`) and asserts `send-user` / `send-advance-user` appear in the faust `cli` group. A subprocess is used deliberately: the rest of the suite imports `example.users.cli` to exercise the command classes, so an in-process check would always pass even if `example.app` did not wire the commands in. The subprocess also asserts the commands are *not* present before `example.app` is imported, so the test cannot pass for the wrong reason.
2. **Command entry behaviour (unit, `tests/test_users_cli.py`)** — drives the `send_user` / `send_advance_user` command objects' `run` methods directly, covering valid payload, missing field, extra field, wrong type and invalid JSON (each asserts the right click error / `OK:` echo and that `topic.send` is/isn't called).
3. **Codec + wiring (unit, `tests/test_users_cli.py`)** — resolves `avro_users` / `avro_advance_users` through `faust.serializers.codecs.get_codec` (the real `faust.codecs` entry-point path) and asserts they are the **same** `FaustSerializer` instances the send helpers pass to `topic.send`; and that each topic is bound to its model, so the send path and the consume path provably share one Avro link.
4. **End-to-end (compose smoke, `scripts/smoke_users.sh`)** — against the running stack it runs `faust -A example.app send-user` / `send-advance-user`, greps the worker logs for the consumed events, and checks that invalid JSON is rejected. Run it with `make smoke-users` (after `docker-compose up -d`).

```bash
docker-compose up -d
make smoke-users
# Expected (abridged):
#   OK: simple user sent to topic 'avro_users'
#   OK: advance user sent to topic 'advance_avro_users'
#   OK: both events reached their consumer agents
#   OK: invalid JSON rejected
#   SMOKE PASS: Users explicit-command -> Avro codec -> topic -> consumer link works
```

## Minimum Verification Steps

After cloning the repo, you can verify **all three example end-to-end paths** (page_views, users, advance_users) with these commands:

```bash
# 1. Build and start everything (Kafka, ZK, SR, Faust worker)
make run-dev
# (wait ~30s for all services to be healthy)

# 2. In a second terminal, verify topics exist
make list-topics
# Expected: page_views, avro_users, advance_avro_users among the listed topics

# 3. Send a Page Views event
make send-page-view-event payload='{"id": "home", "user": "alice"}'
# Watch faust-project logs for: "Event received. Page view Id home"

# 4. Send a Simple User event
make send-user-event payload='{"first_name": "Alice", "last_name": "Smith"}'
# Watch faust-project logs for:
#   "Sent simple user to topic 'avro_users': ..."
#   "Event received in topic avro_users"
#   "First Name: Alice, last name Smith"

# 5. Send an Advance User event
make send-advance-user-event payload='{"first_name": "Bob", "last_name": "Jones", "age": 30}'
# Watch faust-project logs for:
#   "Sent advance user to topic 'advance_avro_users': ..."
#   "Event received in topic advance_avro_users"
#   "First Name: Bob, last name Jones, age 30"

# 6. Try validation errors (expect clear failures, not silent drops):

# Missing 'age' for advance user — should ERROR, not send anything
make send-advance-user-event payload='{"first_name": "Bad", "last_name": "User"}'
# Expected error: "Missing required field(s) for 'advance' user: ['age']"

# Extra field 'email' for simple user — should ERROR
make send-user-event payload='{"first_name": "Bad", "last_name": "User", "email": "x@y"}'
# Expected error: "Unexpected field(s) for 'simple' user: ['email']"

# 7. Run the automated test suite
make test
```

## Tests

Run tests in the container (services must be running so imports resolve):

```bash
make test
```

Or locally with `tox` (requires a virtualenv with the project installed):

```bash
cd faust-project && tox
```

The suite covers (`tests/test_users.py` and `tests/test_users_cli.py`):
- `UserModel` / `AdvanceUserModel` carry the correct serializer names
- `USER_TOPIC_CONFIG` maps simple/advance to the correct topics, subjects and field sets
- `validate_user_payload` rejects missing, extra and wrong-typed fields with clear messages
- `UserModel.from_payload` / `AdvanceUserModel.from_payload` validate before construction
- `send_simple_user` / `send_advance_user` hit the **correct** topic with the **correct** serializer (mocked) — and refuse to send on bad payloads
- `users` / `advance_users` agents correctly consume events put on their streams
- **the `send_user` / `send_advance_user` command entries themselves** (their `run` methods): valid payload dispatches to the right helper/serializer and echoes `OK:`; missing / extra / wrong-type / invalid-JSON inputs raise the right click errors — proving the CLI command contract, not just the helper below it
- **the commands are registered** in the faust `cli` group as `send-user` / `send-advance-user`
- **the `avro_users` / `avro_advance_users` codecs resolve** through `faust.serializers.codecs.get_codec` to the same `FaustSerializer` instances the send path uses, and each topic is bound to its model (send ⇄ consume share one Avro link)
- `page_views` tests run unchanged (regression guard)

## Achievements

* [x] Application examples
* [x] Integration with Schma Registry
* [x] Schema Registry Client
* [x] Custom codecs
* [x] Custom Serializers
* [x] Avro Schemas
* [x] Make Schema Registry Client and Serializers a python package
