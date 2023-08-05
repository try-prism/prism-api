import logging
import time

import boto3
from botocore.exceptions import ClientError
from constants import DYNAMODB_ORGANIZATION_TABLE, DYNAMODB_WHITELIST_TABLE

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

    def put_item(self, table_name: str, item: dict) -> bool:
        try:
            self.client.put_item(
                Item=item,
                TableName=table_name,
            )
        except ClientError as e:
            logger.error(f"table_name={table_name}, item={item}, {str(e)}")
            return False

        return True

    def get_item(self, table_name: str, key: dict) -> dict | None:
        response = self.client.get_item(
            Key=key,
            TableName=table_name,
        )

        if "Item" not in response:
            return None

        return response

    def delete_item(self, table_name: str, key: dict) -> dict | None:
        response = self.client.delete_item(
            TableName=table_name, Key=key, ReturnValues="ALL_OLD"
        )

        if "Item" not in response:
            return None

        return response

    def register_organization(
        self, org_id: str, org_name: str, org_admin_id: str
    ) -> bool:
        timestamp = str(time.time())
        new_organization = {
            "id": {"S": org_id},
            "name": {"S": org_name},
            "admin_id": {"S": org_admin_id},
            "user_list": {"L": [org_admin_id]},
            "index_id": {"S": ""},
            "link_id_map": {"M": {}},
            "document_list": {"L": []},
            "created_at": {"S": timestamp},
            "updated_at": {"S": timestamp},
        }

        response = self.put_item(DYNAMODB_ORGANIZATION_TABLE, new_organization)

        return response

    def get_organization(self, org_id: str) -> dict | None:
        key = {"id": {"S": org_id}}
        response = self.get_item(DYNAMODB_ORGANIZATION_TABLE, key)

        return response

    def add_to_whitelist(self, org_id: str, org_name: str, org_user_id: str) -> bool:
        timestamp = str(time.time())
        new_whitelist_item = {
            "id": {"S": org_user_id},
            "org_name": {"S": org_name},
            "org_id": {"S": org_id},
            "created_at": {"S": timestamp},
        }

        response = self.put_item(DYNAMODB_WHITELIST_TABLE, new_whitelist_item)

        return response
