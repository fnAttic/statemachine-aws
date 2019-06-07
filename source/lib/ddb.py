#!/usr/bin/env python
from datetime import datetime
import json
import boto3


DDB_CLIENT = boto3.client('dynamodb')


StringAttribute = (
    lambda x: {'S': x},
    lambda x: x['S']
)

DateTimeAttribute = (
    # datetime assumed to be in UTC
    lambda x: {'S': x.strftime("%Y-%m-%dT%H:%M:%S")},
    lambda x: datetime.strptime(x['S'], "%Y-%m-%dT%H:%M:%S")
)

IntegerAttribute = (
    lambda x: {'N': str(x)},
    lambda x: int(x['N'])
)

FloatAttribute = (
    lambda x: {'N': str(x)},
    lambda x: float(x['N'])
)

JsonAttribute = (
    lambda x: {'S': json.dumps(x)},
    lambda x: json.loads(x['S'])
)


class Model(object):
    """DDB model"""

    _TABLE_NAME = None
    _FIELDS = []

    @classmethod
    def get_table_name(cls):
        """table name"""
        return cls._TABLE_NAME

    @classmethod
    def serialize(cls, data):
        """serialize data"""
        stored_data = {}
        for field_name, (field_serializer, field_deserializer) in cls._FIELDS:
            value = data.get(field_name)
            if value is not None:
                stored_data[field_name] = field_serializer(value)
        return stored_data

    @classmethod
    def deserialize(cls, stored_data):
        """deserialize data"""
        data = {}
        for field_name, (field_serializer, field_deserializer) in cls._FIELDS:
            value = stored_data.get(field_name)
            if value is not None:
                data[field_name] = field_deserializer(value)
        return data

    @classmethod
    def create(cls, data, **kwargs):
        """create file item"""
        put_data = cls.serialize(data)
        response = DDB_CLIENT.put_item(
            TableName=cls._TABLE_NAME,
            Item=put_data
        )
        return data

    @classmethod
    def get_by_id(cls, id):
        """get item with id"""
        response = DDB_CLIENT.get_item(
            TableName=cls._TABLE_NAME,
            Key={
                'id': {
                    'S': id
                }
            }
        )
        get_data = cls.deserialize(response['Item'])
        return get_data

    @classmethod
    def delete_by_id(cls, id):
        """delete item by id"""
        response = DDB_CLIENT.delete_item(
            TableName=cls._TABLE_NAME,
            Key={
                'id': {
                    'S': id
                }
            }
        )
        return response
