import logging
from typing import Union

import boto3
from constants import DYNAMODB_ORGANIZATION_TABLE

logger = logging.getLogger(__name__)


class DynamoDBService:
    """
    Handles all of the operations related to DynamoDB.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html

    Author: Hwuiwon Kim (hwuiwon.kim@gmail.com)
    """

    def __init__(self):
        self.client = boto3.client("dynamodb")

    def get_client(self):
        return self.client

    def put_item(self, table_name: str, item: dict) -> None:
        self.client.put_item(
            Item=item,
            TableName=table_name,
        )

    def get_item(self, table_name: str, key: dict) -> Union[dict, None]:
        response = self.client.get_item(
            Key=key,
            TableName=table_name,
        )

        if "Item" not in response:
            return None

        return response

    def delete_item(self, table_name: str, key: dict) -> Union[dict, None]:
        response = self.client.delete_item(
            TableName=table_name, Key=key, ReturnValues="ALL_OLD"
        )

        if "Item" not in response:
            return None

        return response

    def get_organization(self, org_id: str) -> Union[dict, None]:
        key = {"id": {"S": org_id}}
        response = self.get_item(DYNAMODB_ORGANIZATION_TABLE, key)

        return response
