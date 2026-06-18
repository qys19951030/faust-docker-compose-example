import logging

from example.app import app
from example.codecs.avro import (
    TOPIC_AVRO_USERS,
    TOPIC_AVRO_ADVANCE_USERS,
    avro_user_serializer,
    avro_advance_user_serializer,
    get_user_topic_config,
    validate_user_payload,
)
from example.users.models import UserModel, AdvanceUserModel

users_topic = app.topic(TOPIC_AVRO_USERS, partitions=1, value_type=UserModel)
advance_users_topic = app.topic(
    TOPIC_AVRO_ADVANCE_USERS, partitions=1, value_type=AdvanceUserModel
)

logger = logging.getLogger(__name__)


async def send_simple_user(payload):
    validate_user_payload(payload, 'simple')
    await users_topic.send(value=payload, value_serializer=avro_user_serializer)
    config = get_user_topic_config('simple')
    logger.info(
        f"Sent simple user to topic '{config['topic']}': {payload}"
    )
    return True


async def send_advance_user(payload):
    validate_user_payload(payload, 'advance')
    await advance_users_topic.send(
        value=payload, value_serializer=avro_advance_user_serializer
    )
    config = get_user_topic_config('advance')
    logger.info(
        f"Sent advance user to topic '{config['topic']}': {payload}"
    )
    return True


@app.agent(users_topic)
async def users(users_stream):
    async for user in users_stream:
        logger.info("Event received in topic avro_users")
        logger.info(
            f"First Name: {user.first_name}, last name {user.last_name}"
        )
        yield user


@app.timer(5.0, on_leader=True)
async def publish_users():
    logger.info('PUBLISHING ON LEADER FOR USERS APP (simple)!')
    user = {"first_name": "foo", "last_name": "bar"}
    await send_simple_user(user)


@app.agent(advance_users_topic)
async def advance_users(users_stream):
    async for user in users_stream:
        logger.info("Event received in topic advance_avro_users")
        logger.info(
            f"First Name: {user.first_name}, last name {user.last_name}, age {user.age}"
        )
        yield user


@app.timer(5.0, on_leader=True)
async def advance_publish_users():
    logger.info('PUBLISHING ON LEADER FOR USERS APP (advance)!')
    user = {"first_name": "foo", "last_name": "bar", "age": 20}
    await send_advance_user(user)
