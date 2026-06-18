import json

import click
from faust.cli import AppCommand, argument

from example.codecs.avro import TOPIC_AVRO_USERS, TOPIC_AVRO_ADVANCE_USERS
from example.users import agents


def _parse_payload(payload_str):
    try:
        return json.loads(payload_str)
    except json.JSONDecodeError as exc:
        raise click.BadParameter(
            f"Invalid JSON payload: {exc}"
        )


class send_user(AppCommand):
    """Send a simple user event to the avro_users topic.

    PAYLOAD must be a JSON string with fields: first_name, last_name.

    Example:
        faust -A example.app send-user \\
            '{"first_name": "Alice", "last_name": "Smith"}'
    """

    options = [argument('payload')]

    async def run(self, payload: str) -> None:
        payload_dict = _parse_payload(payload)
        try:
            await agents.send_simple_user(payload_dict)
        except ValueError as exc:
            raise click.ClickException(str(exc))
        click.echo(f"OK: simple user sent to topic '{TOPIC_AVRO_USERS}'")


class send_advance_user(AppCommand):
    """Send an advance user event to the advance_avro_users topic.

    PAYLOAD must be a JSON string with fields: first_name, last_name, age.

    Example:
        faust -A example.app send-advance-user \\
            '{"first_name": "Bob", "last_name": "Jones", "age": 30}'
    """

    options = [argument('payload')]

    async def run(self, payload: str) -> None:
        payload_dict = _parse_payload(payload)
        try:
            await agents.send_advance_user(payload_dict)
        except ValueError as exc:
            raise click.ClickException(str(exc))
        click.echo(
            f"OK: advance user sent to topic '{TOPIC_AVRO_ADVANCE_USERS}'"
        )
