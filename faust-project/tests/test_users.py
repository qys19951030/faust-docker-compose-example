import pytest
from unittest.mock import AsyncMock, patch

from example.users.models import UserModel, AdvanceUserModel
from example.users.agents import (
    users,
    advance_users,
    users_topic,
    advance_users_topic,
    send_simple_user,
    send_advance_user,
)
from example.codecs.avro import (
    USER_TOPIC_CONFIG,
    TOPIC_AVRO_USERS,
    TOPIC_AVRO_ADVANCE_USERS,
    SERIALIZER_NAME_AVRO_USERS,
    SERIALIZER_NAME_AVRO_ADVANCE_USERS,
    SCHEMA_SUBJECT_AVRO_USERS,
    SCHEMA_SUBJECT_AVRO_ADVANCE_USERS,
    validate_user_payload,
    get_user_topic_config,
)
from example.app import app


@pytest.fixture()
def test_app(event_loop):
    app.finalize()
    app.conf.store = 'memory://'
    app.flow_control.resume()
    return app


class TestModelSerializers:
    def test_user_model_serializer_name(self):
        assert UserModel._options.serializer == SERIALIZER_NAME_AVRO_USERS

    def test_advance_user_model_serializer_name(self):
        assert AdvanceUserModel._options.serializer == SERIALIZER_NAME_AVRO_ADVANCE_USERS

    def test_user_model_kind(self):
        assert UserModel.kind() == 'simple'

    def test_advance_user_model_kind(self):
        assert AdvanceUserModel.kind() == 'advance'


class TestTopicConfigMapping:
    def test_simple_config_topic(self):
        config = get_user_topic_config('simple')
        assert config['topic'] == TOPIC_AVRO_USERS

    def test_simple_config_serializer_name(self):
        config = get_user_topic_config('simple')
        assert config['serializer_name'] == SERIALIZER_NAME_AVRO_USERS

    def test_simple_config_schema_subject(self):
        config = get_user_topic_config('simple')
        assert config['schema_subject'] == SCHEMA_SUBJECT_AVRO_USERS

    def test_simple_config_required_fields(self):
        config = get_user_topic_config('simple')
        assert set(config['required_fields']) == {'first_name', 'last_name'}

    def test_advance_config_topic(self):
        config = get_user_topic_config('advance')
        assert config['topic'] == TOPIC_AVRO_ADVANCE_USERS

    def test_advance_config_serializer_name(self):
        config = get_user_topic_config('advance')
        assert config['serializer_name'] == SERIALIZER_NAME_AVRO_ADVANCE_USERS

    def test_advance_config_schema_subject(self):
        config = get_user_topic_config('advance')
        assert config['schema_subject'] == SCHEMA_SUBJECT_AVRO_ADVANCE_USERS

    def test_advance_config_required_fields(self):
        config = get_user_topic_config('advance')
        assert set(config['required_fields']) == {'first_name', 'last_name', 'age'}

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError) as exc:
            get_user_topic_config('unknown')
        assert "Unknown user kind 'unknown'" in str(exc.value)


class TestValidateUserPayload:
    def test_simple_valid_payload(self):
        payload = {"first_name": "Alice", "last_name": "Smith"}
        assert validate_user_payload(payload, 'simple') is True

    def test_simple_missing_first_name(self):
        payload = {"last_name": "Smith"}
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'simple')
        assert "Missing required field(s)" in str(exc.value)
        assert "first_name" in str(exc.value)

    def test_simple_missing_last_name(self):
        payload = {"first_name": "Alice"}
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'simple')
        assert "Missing required field(s)" in str(exc.value)
        assert "last_name" in str(exc.value)

    def test_simple_extra_field_rejected(self):
        payload = {"first_name": "Alice", "last_name": "Smith", "age": 25}
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'simple')
        assert "Unexpected field(s)" in str(exc.value)
        assert "age" in str(exc.value)

    def test_simple_first_name_wrong_type(self):
        payload = {"first_name": 123, "last_name": "Smith"}
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'simple')
        assert "first_name" in str(exc.value)
        assert "must be a string" in str(exc.value)

    def test_advance_valid_payload(self):
        payload = {"first_name": "Bob", "last_name": "Jones", "age": 30}
        assert validate_user_payload(payload, 'advance') is True

    def test_advance_missing_age(self):
        payload = {"first_name": "Bob", "last_name": "Jones"}
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'advance')
        assert "Missing required field(s)" in str(exc.value)
        assert "age" in str(exc.value)

    def test_advance_age_wrong_type(self):
        payload = {"first_name": "Bob", "last_name": "Jones", "age": "thirty"}
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'advance')
        assert "age" in str(exc.value)
        assert "must be an int" in str(exc.value)

    def test_advance_extra_field_rejected(self):
        payload = {
            "first_name": "Bob",
            "last_name": "Jones",
            "age": 30,
            "email": "bob@example.com",
        }
        with pytest.raises(ValueError) as exc:
            validate_user_payload(payload, 'advance')
        assert "Unexpected field(s)" in str(exc.value)
        assert "email" in str(exc.value)

    def test_non_dict_payload(self):
        with pytest.raises(ValueError) as exc:
            validate_user_payload("not a dict", 'simple')
        assert "Payload must be a dict" in str(exc.value)


class TestModelFromPayload:
    def test_user_model_from_valid_payload(self):
        payload = {"first_name": "Alice", "last_name": "Smith"}
        user = UserModel.from_payload(payload)
        assert user.first_name == "Alice"
        assert user.last_name == "Smith"

    def test_user_model_from_invalid_payload_raises(self):
        payload = {"first_name": "Alice"}
        with pytest.raises(ValueError):
            UserModel.from_payload(payload)

    def test_advance_user_model_from_valid_payload(self):
        payload = {"first_name": "Bob", "last_name": "Jones", "age": 30}
        user = AdvanceUserModel.from_payload(payload)
        assert user.first_name == "Bob"
        assert user.last_name == "Jones"
        assert user.age == 30

    def test_advance_user_model_from_invalid_payload_raises(self):
        payload = {"first_name": "Bob", "last_name": "Jones", "age": "old"}
        with pytest.raises(ValueError):
            AdvanceUserModel.from_payload(payload)


class TestSendFunctions:
    @pytest.mark.asyncio()
    async def test_send_simple_user_calls_topic_send_with_correct_args(self, test_app):
        payload = {"first_name": "Alice", "last_name": "Smith"}

        with patch.object(
            users_topic, 'send', new_callable=AsyncMock
        ) as mock_send:
            result = await send_simple_user(payload)

            assert result is True
            mock_send.assert_awaited_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs['value'] == payload

            from example.codecs.avro import avro_user_serializer
            assert call_kwargs['value_serializer'] is avro_user_serializer

    @pytest.mark.asyncio()
    async def test_send_simple_user_rejects_bad_payload(self, test_app):
        payload = {"first_name": "Alice"}
        with patch.object(
            users_topic, 'send', new_callable=AsyncMock
        ) as mock_send:
            with pytest.raises(ValueError) as exc:
                await send_simple_user(payload)
            assert "Missing required field(s)" in str(exc.value)
            mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_send_advance_user_calls_topic_send_with_correct_args(self, test_app):
        payload = {"first_name": "Bob", "last_name": "Jones", "age": 30}

        with patch.object(
            advance_users_topic, 'send', new_callable=AsyncMock
        ) as mock_send:
            result = await send_advance_user(payload)

            assert result is True
            mock_send.assert_awaited_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs['value'] == payload

            from example.codecs.avro import avro_advance_user_serializer
            assert call_kwargs['value_serializer'] is avro_advance_user_serializer

    @pytest.mark.asyncio()
    async def test_send_advance_user_rejects_bad_payload(self, test_app):
        payload = {"first_name": "Bob", "last_name": "Jones"}
        with patch.object(
            advance_users_topic, 'send', new_callable=AsyncMock
        ) as mock_send:
            with pytest.raises(ValueError) as exc:
                await send_advance_user(payload)
            assert "Missing required field(s)" in str(exc.value)
            mock_send.assert_not_awaited()

    @pytest.mark.asyncio()
    async def test_simple_and_advance_use_different_topics(self, test_app):
        simple_payload = {"first_name": "Alice", "last_name": "Smith"}
        advance_payload = {"first_name": "Bob", "last_name": "Jones", "age": 30}

        with patch.object(
            users_topic, 'send', new_callable=AsyncMock
        ) as mock_simple_send, patch.object(
            advance_users_topic, 'send', new_callable=AsyncMock
        ) as mock_advance_send:
            await send_simple_user(simple_payload)
            await send_advance_user(advance_payload)

            mock_simple_send.assert_awaited_once()
            mock_advance_send.assert_awaited_once()

            simple_kwargs = mock_simple_send.call_args[1]
            advance_kwargs = mock_advance_send.call_args[1]

            from example.codecs.avro import (
                avro_user_serializer as simple_ser,
                avro_advance_user_serializer as advance_ser,
            )
            assert simple_kwargs['value_serializer'] is simple_ser
            assert advance_kwargs['value_serializer'] is advance_ser
            assert simple_ser is not advance_ser


class TestAgents:
    @pytest.mark.asyncio()
    async def test_users_agent_processes_event(self, test_app):
        async with users.test_context() as agent:
            user = UserModel(first_name='Test', last_name='User')
            event = await agent.put(user)
            assert event.value.first_name == 'Test'
            assert event.value.last_name == 'User'

    @pytest.mark.asyncio()
    async def test_advance_users_agent_processes_event(self, test_app):
        async with advance_users.test_context() as agent:
            user = AdvanceUserModel(
                first_name='Advance', last_name='User', age=42
            )
            event = await agent.put(user)
            assert event.value.first_name == 'Advance'
            assert event.value.last_name == 'User'
            assert event.value.age == 42


class TestTopicDefinitions:
    def test_users_topic_name(self):
        assert TOPIC_AVRO_USERS in users_topic.topics

    def test_advance_users_topic_name(self):
        assert TOPIC_AVRO_ADVANCE_USERS in advance_users_topic.topics

    def test_users_topic_value_type(self):
        assert users_topic.value_type is UserModel

    def test_advance_users_topic_value_type(self):
        assert advance_users_topic.value_type is AdvanceUserModel
