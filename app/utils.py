"""General utils functions."""
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer


def divide_list(target_list: list, item_size: int) -> list[list]:
    n = len(target_list)
    res = [None] * ((n - 1) // item_size + 1)

    for i in range(0, n, item_size):
        res[i // item_size] = target_list[i : i + item_size]

    return res


def serialize(object: dict) -> dict:
    serializer = TypeSerializer()
    return {k: serializer.serialize(v) for k, v in object.items()}


def deserialize(object: dict) -> dict:
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in object.items()}
