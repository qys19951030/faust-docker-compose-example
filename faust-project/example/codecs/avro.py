from schema_registry.client import SchemaRegistryClient, schema
from schema_registry.serializers import FaustSerializer

from simple_settings import settings


TOPIC_AVRO_USERS = 'avro_users'
TOPIC_AVRO_ADVANCE_USERS = 'advance_avro_users'

SERIALIZER_NAME_AVRO_USERS = 'avro_users'
SERIALIZER_NAME_AVRO_ADVANCE_USERS = 'avro_advance_users'

SCHEMA_SUBJECT_AVRO_USERS = 'users'
SCHEMA_SUBJECT_AVRO_ADVANCE_USERS = 'advance_users'


client = SchemaRegistryClient(url=settings.SCHEMA_REGISTRY_URL)


_avro_user_schema_dict = {
    "type": "record",
    "namespace": "com.example",
    "name": "AvroUsers",
    "fields": [
        {"name": "first_name", "type": "string"},
        {"name": "last_name", "type": "string"}
    ]
}

avro_user_schema = schema.AvroSchema(_avro_user_schema_dict)
avro_user_serializer = FaustSerializer(
    client, SCHEMA_SUBJECT_AVRO_USERS, avro_user_schema
)


_avro_advance_user_schema_dict = {
    "type": "record",
    "namespace": "com.example",
    "name": "AdvanceAvroUsers",
    "fields": [
        {"name": "first_name", "type": "string"},
        {"name": "last_name", "type": "string"},
        {"name": "age", "type": "int"}
    ]
}

avro_advance_user_schema = schema.AvroSchema(_avro_advance_user_schema_dict)
avro_advance_user_serializer = FaustSerializer(
    client, SCHEMA_SUBJECT_AVRO_ADVANCE_USERS, avro_advance_user_schema
)


USER_TOPIC_CONFIG = {
    'simple': {
        'topic': TOPIC_AVRO_USERS,
        'serializer_name': SERIALIZER_NAME_AVRO_USERS,
        'serializer': avro_user_serializer,
        'schema_subject': SCHEMA_SUBJECT_AVRO_USERS,
        'required_fields': ('first_name', 'last_name'),
        'allowed_fields': ('first_name', 'last_name'),
    },
    'advance': {
        'topic': TOPIC_AVRO_ADVANCE_USERS,
        'serializer_name': SERIALIZER_NAME_AVRO_ADVANCE_USERS,
        'serializer': avro_advance_user_serializer,
        'schema_subject': SCHEMA_SUBJECT_AVRO_ADVANCE_USERS,
        'required_fields': ('first_name', 'last_name', 'age'),
        'allowed_fields': ('first_name', 'last_name', 'age'),
    },
}


def get_user_topic_config(kind):
    if kind not in USER_TOPIC_CONFIG:
        raise ValueError(
            f"Unknown user kind '{kind}'. "
            f"Must be one of: {list(USER_TOPIC_CONFIG.keys())}"
        )
    return USER_TOPIC_CONFIG[kind]


def validate_user_payload(payload, kind):
    config = get_user_topic_config(kind)
    required = config['required_fields']
    allowed = set(config['allowed_fields'])

    if not isinstance(payload, dict):
        raise ValueError(
            f"Payload must be a dict, got {type(payload).__name__}"
        )

    missing = [f for f in required if f not in payload]
    if missing:
        raise ValueError(
            f"Missing required field(s) for '{kind}' user: {missing}. "
            f"Required fields are: {list(required)}"
        )

    extra = [f for f in payload.keys() if f not in allowed]
    if extra:
        raise ValueError(
            f"Unexpected field(s) for '{kind}' user: {extra}. "
            f"Only these fields are allowed: {list(allowed)}"
        )

    if kind == 'advance' and not isinstance(payload.get('age'), int):
        raise ValueError(
            f"Field 'age' must be an int, got {type(payload.get('age')).__name__}"
        )

    for str_field in ('first_name', 'last_name'):
        if str_field in payload and not isinstance(payload.get(str_field), str):
            raise ValueError(
                f"Field '{str_field}' must be a string, "
                f"got {type(payload.get(str_field)).__name__}"
            )

    return True


def avro_user_codec():
    return avro_user_serializer


def avro_advance_user_codec():
    return avro_advance_user_serializer
