import json

import click
import pytest
from unittest.mock import AsyncMock, patch

from faust.serializers import codecs as faust_codecs

from example.users.cli import send_user, send_advance_user, _parse_payload
from example.users.agents import users_topic, advance_users_topic
from example.users.models import UserModel, AdvanceUserModel
from example.codecs.avro import (
    TOPIC_AVRO_USERS,
    TOPIC_AVRO_ADVANCE_USERS,
    SERIALIZER_NAME_AVRO_USERS,
    SERIALIZER_NAME_AVRO_ADVANCE_USERS,
    avro_user_serializer,
    avro_advance_user_serializer,
)


def _make_command(cls):
    return object.__new__(cls)


VALID_SIMPLE = {"first_name": "Alice", "last_name": "Smith"}
VALID_ADVANCE = {"first_name": "Bob", "last_name": "Jones", "age": 30}


class TestSendUserCommandEntry:
    """Exercise the send_user COMMAND entry (its run method), not the helper."""

    @pytest.mark.asyncio()
    async def test_valid_payload_dispatches_and_echoes(self, capsys):
        cmd = _make_command(send_user)
        payload = json.dumps(VALID_SIMPLE)
        with patch.object(users_topic, 'send', new_callable=AsyncMock) as mock_send:
            await cmd.run(payload=payload)
        mock_send.assert_awaited_once()
        kwargs = mock_send.call_args[1]
        assert kwargs['value'] == VALID_SIMPLE
        assert kwargs['value_serializer'] is avro_user_serializer
        assert ("OK: simple user sent to topic 'avro_users'"
                in capsys.readouterr().out)

    @pytest.mark.asyncio()
    async def test_missing_field_raises_click_exception(self):
        cmd = _make_command(send_user)
        payload = json.dumps({"first_name": "Alice"})
        with patch.object(users_topic, 'send', new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.ClickException) as exc:
                await cmd.run(payload=payload)
        assert "Missing required field" in exc.value.message
        assert "last_name" in exc.value.message
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_extra_field_raises_click_exception(self):
        cmd = _make_command(send_user)
        payload = json.dumps(
            {"first_name": "Alice", "last_name": "Smith", "age": 25}
        )
        with patch.object(users_topic, 'send', new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.ClickException) as exc:
                await cmd.run(payload=payload)
        assert "Unexpected field" in exc.value.message
        assert "age" in exc.value.message
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_wrong_type_raises_click_exception(self):
        cmd = _make_command(send_user)
        payload = json.dumps({"first_name": 123, "last_name": "Smith"})
        with patch.object(users_topic, 'send', new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.ClickException) as exc:
                await cmd.run(payload=payload)
        assert "must be a string" in exc.value.message
        assert "first_name" in exc.value.message
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_invalid_json_raises_bad_parameter(self):
        cmd = _make_command(send_user)
        with patch.object(users_topic, 'send', new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.BadParameter) as exc:
                await cmd.run(payload="{not json")
        assert "Invalid JSON payload" in exc.value.message
        mock_send.assert_not_awaited()


class TestSendAdvanceUserCommandEntry:
    """Exercise the send_advance_user COMMAND entry (its run method)."""

    @pytest.mark.asyncio()
    async def test_valid_payload_dispatches_and_echoes(self, capsys):
        cmd = _make_command(send_advance_user)
        payload = json.dumps(VALID_ADVANCE)
        with patch.object(advance_users_topic, 'send',
                         new_callable=AsyncMock) as mock_send:
            await cmd.run(payload=payload)
        mock_send.assert_awaited_once()
        kwargs = mock_send.call_args[1]
        assert kwargs['value'] == VALID_ADVANCE
        assert kwargs['value_serializer'] is avro_advance_user_serializer
        assert ("OK: advance user sent to topic 'advance_avro_users'"
                in capsys.readouterr().out)

    @pytest.mark.asyncio()
    async def test_missing_age_raises_click_exception(self):
        cmd = _make_command(send_advance_user)
        payload = json.dumps({"first_name": "Bob", "last_name": "Jones"})
        with patch.object(advance_users_topic, 'send',
                         new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.ClickException) as exc:
                await cmd.run(payload=payload)
        assert "Missing required field" in exc.value.message
        assert "age" in exc.value.message
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_extra_field_raises_click_exception(self):
        cmd = _make_command(send_advance_user)
        payload = json.dumps({
            "first_name": "Bob", "last_name": "Jones", "age": 30,
            "email": "bob@example.com",
        })
        with patch.object(advance_users_topic, 'send',
                         new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.ClickException) as exc:
                await cmd.run(payload=payload)
        assert "Unexpected field" in exc.value.message
        assert "email" in exc.value.message
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_age_wrong_type_raises_click_exception(self):
        cmd = _make_command(send_advance_user)
        payload = json.dumps(
            {"first_name": "Bob", "last_name": "Jones", "age": "thirty"}
        )
        with patch.object(advance_users_topic, 'send',
                         new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.ClickException) as exc:
                await cmd.run(payload=payload)
        assert "must be an int" in exc.value.message
        mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_invalid_json_raises_bad_parameter(self):
        cmd = _make_command(send_advance_user)
        with patch.object(advance_users_topic, 'send',
                         new_callable=AsyncMock) as mock_send:
            with pytest.raises(click.BadParameter) as exc:
                await cmd.run(payload="[1, 2")
        assert "Invalid JSON payload" in exc.value.message
        mock_send.assert_not_awaited()


class TestParsePayload:
    def test_parses_valid_json(self):
        assert _parse_payload('{"a": 1}') == {"a": 1}

    def test_invalid_json_raises_bad_parameter(self):
        with pytest.raises(click.BadParameter) as exc:
            _parse_payload("not json")
        assert "Invalid JSON payload" in exc.value.message


class TestCommandRegistrationViaAppImport:
    """Layer 1 — prove the REAL `faust -A example.app` import path registers the
    commands, *without* this test importing `example.users.cli` itself.

    Why a subprocess: the rest of this file (and the rest of the suite) imports
    `example.users.cli` to exercise the command classes, so by the time any
    in-process test runs the commands are already registered in the shared
    `faust.cli.base.cli` group — an in-process ``'send-user' in cli.commands``
    check would therefore pass even if `example.app` did not wire the commands
    in at all (a false positive). A clean interpreter that imports ONLY
    `example.app` is the only honest way to prove the wiring. `tests.conftest`
    is imported first solely for the Python 3.12 shims that let faust import
    locally; it does not import `example.users.cli`.
    """

    @staticmethod
    def _run_in_clean_interpreter(script: str):
        import os
        import subprocess
        import sys
        env = dict(os.environ)
        env['SIMPLE_SETTINGS'] = env.get('SIMPLE_SETTINGS') or 'settings'
        env['PYTHONPATH'] = os.pathsep.join(
            p for p in [os.getcwd(), env.get('PYTHONPATH', '')] if p
        )
        return subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True,
            text=True,
            env=env,
            cwd=os.getcwd(),
            timeout=60,
        )

    def test_importing_only_example_app_registers_both_commands(self):
        script = (
            "import tests.conftest; "
            "from faust.cli.base import cli; "
            "assert 'send-user' not in cli.commands, "
            "'precondition: command registered before example.app import'; "
            "import example.app; "
            "assert 'send-user' in cli.commands, "
            "'send-user not registered by importing example.app'; "
            "assert 'send-advance-user' in cli.commands, "
            "'send-advance-user not registered by importing example.app'; "
            "print('OK')"
        )
        result = self._run_in_clean_interpreter(script)
        assert result.returncode == 0, (
            "expected `import example.app` alone to register the Users "
            f"commands.\nreturncode={result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert 'OK' in result.stdout


class TestCodecRegistration:
    """Prove the avro_users / avro_advance_users codecs are really registered
    via the faust.codecs entry points and resolve to the right serializers."""

    def test_avro_users_entry_point_resolves_to_serializer(self):
        resolved = faust_codecs.get_codec(SERIALIZER_NAME_AVRO_USERS)
        assert resolved is avro_user_serializer
        assert SERIALIZER_NAME_AVRO_USERS in faust_codecs.codecs

    def test_avro_advance_users_entry_point_resolves_to_serializer(self):
        resolved = faust_codecs.get_codec(SERIALIZER_NAME_AVRO_ADVANCE_USERS)
        assert resolved is avro_advance_user_serializer
        assert SERIALIZER_NAME_AVRO_ADVANCE_USERS in faust_codecs.codecs

    def test_entry_points_declared_in_setup(self):
        import importlib.metadata as m
        eps = m.entry_points()
        group = (eps.get('faust.codecs', []) if hasattr(eps, 'get')
                 else list(eps.select(group='faust.codecs')))
        names = {e.name for e in group}
        assert SERIALIZER_NAME_AVRO_USERS in names
        assert SERIALIZER_NAME_AVRO_ADVANCE_USERS in names


class TestSendConsumeWiring:
    """Tie together the model, topic, codec name and serializer so that the
    send path and the consume path are provably using the same Avro link."""

    def test_users_topic_bound_to_user_model(self):
        assert users_topic.value_type is UserModel
        assert TOPIC_AVRO_USERS in users_topic.topics

    def test_advance_users_topic_bound_to_advance_model(self):
        assert advance_users_topic.value_type is AdvanceUserModel
        assert TOPIC_AVRO_ADVANCE_USERS in advance_users_topic.topics

    def test_send_and_consume_resolve_to_same_serializer(self):
        faust_codecs.get_codec(SERIALIZER_NAME_AVRO_USERS)
        faust_codecs.get_codec(SERIALIZER_NAME_AVRO_ADVANCE_USERS)
        # send path: helpers pass these serializer instances to topic.send
        # consume path: faust resolves the model serializer name via get_codec
        assert UserModel._options.serializer == SERIALIZER_NAME_AVRO_USERS
        assert (faust_codecs.get_codec(UserModel._options.serializer)
                is avro_user_serializer)
        assert AdvanceUserModel._options.serializer == SERIALIZER_NAME_AVRO_ADVANCE_USERS
        assert (faust_codecs.get_codec(AdvanceUserModel._options.serializer)
                is avro_advance_user_serializer)
