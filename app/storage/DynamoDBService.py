import logging
import time

import boto3
from botocore.exceptions import ClientError
from constants import (
    DYNAMODB_ORGANIZATION_TABLE,
    DYNAMODB_USER_TABLE,
    DYNAMODB_WHITELIST_TABLE,
)
from exceptions import PrismDBException, PrismDBExceptionCode
from models import (
    get_organization_key,
    get_user_key,
    to_organization_model,
    to_user_model,
)

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
        try:
            self.client.put_item(
                Item=item,
                TableName=table_name,
            )
        except ClientError as e:
            logger.error("table_name=%s, item=%s, error=%s", table_name, item, str(e))
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_PUT_ERROR,
                message="Could not append item to table",
            )

    def get_item(self, table_name: str, key: dict) -> dict:
        response = self.client.get_item(
            Key=key,
            TableName=table_name,
        )

        if "Item" not in response:
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_DOES_NOT_EXIST,
                message="Item does not exist",
            )

        return response

    def update_item(
        self, table_name: str, key: dict, field_name: str, field_value: dict
    ) -> None:
        try:
            self.client.update_item(
                TableName=table_name,
                Key=key,
                UpdateExpression=f"SET {field_name} = :v, updated_at = :ua",
                ExpressionAttributeValues={
                    ":v": field_value,
                    ":ua": {"S": str(time.time())},
                },
            )
        except ClientError as e:
            logger.error(
                "table_name=%s, key=%s, field_name=%s, field_value=%s, error=%s",
                table_name,
                key,
                field_name,
                field_value,
                str(e),
            )
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_UPDATE_ERROR,
                message="Could not update item to table",
            )

    def delete_item(self, table_name: str, key: dict) -> dict:
        response = self.client.delete_item(
            TableName=table_name, Key=key, ReturnValues="ALL_OLD"
        )

        if "Item" not in response:
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_DOES_NOT_EXIST,
                message="Item does not exist",
            )

        return response

    def register_organization(
        self, org_id: str, org_name: str, org_admin_id: str
    ) -> None:
        timestamp = str(time.time())
        new_organization = {
            "id": {"S": org_id},
            "name": {"S": org_name},
            "admin_id": {"S": org_admin_id},
            "user_list": {"L": [org_admin_id]},
            "invited_user_list": {"L": []},
            "index_id": {"S": ""},
            "link_id_map": {"M": {}},
            "document_list": {"L": []},
            "created_at": {"S": timestamp},
            "updated_at": {"S": timestamp},
        }

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, new_organization)

    def get_organization(self, org_id: str) -> dict:
        key = get_organization_key(org_id)

        try:
            return self.get_item(DYNAMODB_ORGANIZATION_TABLE, key)
        except PrismDBException as e:
            e.message = "Could not find organization"
            raise e

    def remove_organization(self, org_id: str, org_admin_id: str) -> dict:
        key = get_organization_key(org_id)

        try:
            response = self.get_item(DYNAMODB_ORGANIZATION_TABLE, key)
        except PrismDBException as e:
            e.message = "Could not find organization"
            raise e

        org_item = to_organization_model(response)

        if org_item.admin_id != org_admin_id:
            raise PrismDBException(
                code=PrismDBExceptionCode.NOT_ENOUGH_PERMISSION,
                message="You don't have permission to access this",
            )

        return self.delete_item(DYNAMODB_ORGANIZATION_TABLE, key)

    def modify_whitelist(
        self, org_id: str, org_name: str, org_user_id: str, is_remove: bool
    ) -> None:
        try:
            if is_remove:
                self.delete_item(
                    table_name=DYNAMODB_WHITELIST_TABLE, key={"S": org_user_id}
                )
            else:
                timestamp = str(time.time())
                new_whitelist_item = {
                    "id": {"S": org_user_id},
                    "org_name": {"S": org_name},
                    "org_id": {"S": org_id},
                    "created_at": {"S": timestamp},
                }

                self.put_item(DYNAMODB_WHITELIST_TABLE, new_whitelist_item)
        except PrismDBException as e:
            word = "remove" if is_remove else "add"
            e.message = f"Failed to {word} user to the whitelist"
            raise e

    def modify_invited_users_list(
        self, org_id: str, org_user_id: str, is_remove: bool
    ) -> None:
        response = self.get_organization(org_id)
        org_item = to_organization_model(response)
        invited_user_list = org_item.invited_user_list

        if is_remove:
            if org_user_id not in invited_user_list:
                raise PrismDBException(
                    code=PrismDBExceptionCode.USER_NOT_INVITED,
                    message="User is not invited",
                )

            invited_user_list.remove(org_user_id)
        else:
            if org_user_id in invited_user_list:
                raise PrismDBException(
                    code=PrismDBExceptionCode.USER_ALREADY_INVITED,
                    message="User is already invited",
                )

            invited_user_list.append(org_user_id)

        try:
            self.update_item(
                table_name=DYNAMODB_ORGANIZATION_TABLE,
                key=get_organization_key(org_id),
                field_name="invited_user_list",
                field_value={"L": invited_user_list},
            )
        except PrismDBException as e:
            word = "remove" if is_remove else "add"
            e.message = f"Failed to {word} user to the invited user list"
            raise e

    def get_whitelist_user_data(self, user_id: str) -> dict:
        key = get_user_key(user_id)

        try:
            response = self.get_item(DYNAMODB_WHITELIST_TABLE, key)
        except PrismDBException as e:
            e.message = "User is not invited to join"
            raise e

        return response

    def register_user(
        self, id: str, email: str, name: str, organization_id: str
    ) -> None:
        timestamp = str(time.time())
        new_user = {
            "id": {"S": id},
            "email": {"S": email},
            "name": {"S": name},
            "organization_id": {"S": organization_id},
            "access_control": {"M": {}},
            "created_at": {"S": timestamp},
            "updated_at": {"S": timestamp},
        }

        self.put_item(DYNAMODB_USER_TABLE, new_user)
        org_response = self.get_organization(organization_id)

        org_item = to_organization_model(org_response)
        user_list = org_item.user_list
        user_list.append(id)

        try:
            self.update_item(
                table_name=DYNAMODB_ORGANIZATION_TABLE,
                key=get_organization_key(organization_id),
                field_name="user_list",
                field_value={"L": user_list},
            )
        except PrismDBException as e:
            e.message = "Could not add user to organization"
            raise e

    def get_user(self, user_id: str) -> dict:
        try:
            response = self.get_item(DYNAMODB_USER_TABLE, get_user_key(user_id))
        except PrismDBException as e:
            e.message = "Could not find user"
            raise e

        return response

    def remove_user(self, user_id: str, org_admin_id: str) -> dict:
        response = self.get_user(user_id)
        user_model = to_user_model(response)
        org_response = self.get_organization(org_id=user_model.organization_id)
        org_model = to_organization_model(org_response)

        if org_model.admin_id != org_admin_id:
            raise PrismDBException(
                code=PrismDBExceptionCode.NOT_ENOUGH_PERMISSION,
                message="You don't have permission to remove user",
            )

        self.delete_item(DYNAMODB_USER_TABLE, get_user_key(user_id))
        response = self.get_organization(user_model.organization_id)
        org_item = to_organization_model(response)
        user_list = org_item.user_list

        if user_id in user_list:
            user_list.remove(user_id)
            self.update_item(
                table_name=DYNAMODB_ORGANIZATION_TABLE,
                key=get_organization_key(user_model.organization_id),
                field_name="user_list",
                field_value={"L": user_list},
            )
        else:
            raise PrismDBException(
                code=PrismDBExceptionCode.USER_DOES_NOT_EXIST,
                message="User does not exist",
            )
