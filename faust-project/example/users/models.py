import faust

from dataclasses_avroschema import AvroModel

from example.codecs.avro import (
    SERIALIZER_NAME_AVRO_USERS,
    SERIALIZER_NAME_AVRO_ADVANCE_USERS,
)


class UserModel(faust.Record, serializer=SERIALIZER_NAME_AVRO_USERS):
    first_name: str
    last_name: str

    @classmethod
    def kind(cls):
        return 'simple'

    @classmethod
    def from_payload(cls, payload):
        from example.codecs.avro import validate_user_payload
        validate_user_payload(payload, cls.kind())
        return cls(**payload)


class AdvanceUserModel(faust.Record, AvroModel, serializer=SERIALIZER_NAME_AVRO_ADVANCE_USERS):
    first_name: str
    last_name: str
    age: int

    @classmethod
    def kind(cls):
        return 'advance'

    @classmethod
    def from_payload(cls, payload):
        from example.codecs.avro import validate_user_payload
        validate_user_payload(payload, cls.kind())
        return cls(**payload)
