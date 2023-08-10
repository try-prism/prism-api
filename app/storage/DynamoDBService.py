import logging
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError
from constants import (
    DYNAMODB_FILE_TABLE,
    DYNAMODB_ORGANIZATION_TABLE,
    DYNAMODB_USER_TABLE,
    DYNAMODB_WHITELIST_TABLE,
)
from exceptions import PrismDBException, PrismDBExceptionCode
from merge.resources.filestorage.types import File
from models import (
    OrganizationModel,
    UserModel,
    WhitelistModel,
    get_file_key,
    get_organization_key,
    get_user_key,
    to_organization_model,
    to_user_model,
    to_whitelist_model,
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
        self.resource = boto3.resource("dynamodb")

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

    def batch_get_item(
        self, table_name: str, field_name: str, field_values: list[str]
    ) -> dict:
        key = {table_name: {"Keys": [{field_name: item} for item in field_values]}}
        response = self.client.batch_get_item(RequestItems=key)

        if "Responses" not in response:
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_BATCH_GET_ERROR,
                message="Failed to get items from table",
            )

        retrieved = {}

        for key in response["Responses"]:
            retrieved[key] += response["Responses"][key]

        return retrieved

    def batch_put_item(self, table_name: str, items: list[dict]) -> None:
        try:
            table = self.resource.Table(table_name)
        except Exception as e:
            logger.error(
                "table_name=%s, len(items)=%s, error=%s", table_name, len(items), str(e)
            )
            raise PrismDBException(
                code=PrismDBExceptionCode.COULD_NOT_CREATE_TABLE,
                message="Could not create table from resource",
            )

        with table.batch_writer() as batch:
            for i in range(len(items)):
                try:
                    batch.put_item(Item=items[i])
                except Exception as e:
                    logger.error(
                        "table_name=%s, item=%s, error=%s",
                        table_name,
                        items[i],
                        str(e),
                    )

    def batch_delete_item(self, table_name: str, keys: list[dict]) -> None:
        try:
            table = self.resource.Table(table_name)
        except Exception as e:
            logger.error(
                "table_name=%s, len(keys)=%s, error=%s", table_name, len(keys), str(e)
            )
            raise PrismDBException(
                code=PrismDBExceptionCode.COULD_NOT_CREATE_TABLE,
                message="Could not create table from resource",
            )

        with table.batch_writer() as batch:
            for i in range(len(keys)):
                try:
                    batch.delete_item(Key=keys[i])
                except Exception as e:
                    logger.error(
                        "table_name=%s, key=%s, error=%s",
                        table_name,
                        keys[i],
                        str(e),
                    )

    def update_item(
        self, table_name: str, key: dict, field_name: str, field_value: Any
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
        self, org_id: str, org_name: str, org_email: str, org_admin_id: str
    ) -> None:
        timestamp = str(time.time())
        new_organization = {
            "id": {"S": org_id},
            "name": {"S": org_name},
            "email": {"S": org_email},
            "admin_id": {"S": org_admin_id},
            "user_list": {"L": [org_admin_id]},
            "invited_user_list": {"L": []},
            "link_id_map": {"M": {}},
            "document_list": {"L": []},
            "created_at": {"S": timestamp},
            "updated_at": {"S": timestamp},
        }

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, new_organization)

    def get_organization(self, org_id: str) -> OrganizationModel:
        key = get_organization_key(org_id)

        try:
            response = self.get_item(DYNAMODB_ORGANIZATION_TABLE, key)
            return to_organization_model(response)
        except PrismDBException as e:
            e.message = "Could not find organization"
            raise

    def remove_organization(self, org_id: str, org_admin_id: str) -> dict:
        key = get_organization_key(org_id)

        try:
            response = self.get_item(DYNAMODB_ORGANIZATION_TABLE, key)
        except PrismDBException as e:
            e.message = "Could not find organization"
            raise

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
            raise

    def modify_invited_users_list(
        self, org_id: str, org_user_id: str, is_remove: bool
    ) -> None:
        organization = self.get_organization(org_id)
        invited_user_list = organization.invited_user_list

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
            raise

    def get_whitelist_user_data(self, user_id: str) -> WhitelistModel:
        key = get_user_key(user_id)

        try:
            response = self.get_item(DYNAMODB_WHITELIST_TABLE, key)
            return to_whitelist_model(response)
        except PrismDBException as e:
            e.message = "User is not invited to join"
            raise

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
        organization = self.get_organization(organization_id)
        user_list = organization.user_list
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
            raise

    def get_user(self, user_id: str) -> UserModel:
        try:
            response = self.get_item(DYNAMODB_USER_TABLE, get_user_key(user_id))
            return to_user_model(response)
        except PrismDBException as e:
            e.message = "Could not find user"
            raise

    def remove_user(self, user_id: str, org_admin_id: str) -> dict:
        user = self.get_user(user_id)
        organization = self.get_organization(org_id=user.organization_id)

        if organization.admin_id != org_admin_id:
            raise PrismDBException(
                code=PrismDBExceptionCode.NOT_ENOUGH_PERMISSION,
                message="You don't have permission to remove user",
            )

        self.delete_item(DYNAMODB_USER_TABLE, get_user_key(user_id))
        user_list = organization.user_list

        if user_id in user_list:
            user_list.remove(user_id)
            self.update_item(
                table_name=DYNAMODB_ORGANIZATION_TABLE,
                key=get_organization_key(user.organization_id),
                field_name="user_list",
                field_value={"L": user_list},
            )
        else:
            raise PrismDBException(
                code=PrismDBExceptionCode.USER_DOES_NOT_EXIST,
                message="User does not exist",
            )

    def add_integration(self, org_id: str, account_token: str, status: str) -> None:
        response = self.get_organization(org_id)
        org_item = to_organization_model(response)

        timestamp = str(time.time())
        link_id_map = org_item.link_id_map
        link_id_map[account_token] = {
            "M": {
                "source": {"S": "UNKNOWN"},
                "created": {"S": timestamp},
                "status": {"S": status},
            }
        }

        self.update_item(
            DYNAMODB_ORGANIZATION_TABLE,
            get_organization_key(org_id),
            field_name="link_id_map",
            field_value=link_id_map,
        )

    def modify_organization_files(
        self, org_id: str, file_id: str, is_remove: bool
    ) -> None:
        response = self.get_organization(org_id)
        org_item = to_organization_model(response)

        document_list = org_item.document_list
        if is_remove:
            if file_id in document_list:
                document_list.remove(file_id)
        else:
            if file_id not in document_list:
                document_list.append(file_id)

        self.update_item(
            DYNAMODB_ORGANIZATION_TABLE,
            get_organization_key(org_id),
            field_name="document_list",
            field_value=document_list,
        )

    def add_file(self, file: File) -> None:
        new_file = {
            "id": {"S": file.id or ""},
            "remote_id": {"S": file.remote_id or ""},
            "name": {"S": file.name or ""},
            "file_url": {"S": file.file_url or ""},
            "file_thumbnail_url": {"S": file.file_thumbnail_url or ""},
            "size": {"N": file.size or 0},
            "mime_type": {"S": file.mime_type or ""},
            "description": {"S": file.description or ""},
            "folder": {"S": file.folder or ""},
            "permissions": {"L": file.permissions or []},
            "drive": {"S": file.drive or ""},
            "remote_created_at": {"S": file.remote_created_at or ""},
            "remote_updated_at": {"S": file.remote_updated_at or ""},
            "remote_was_deleted": {"BOOL": file.remote_was_deleted or False},
            "modified_at": {"S": file.modified_at or ""},
            "field_mappings": {"M": file.field_mappings or {}},
            "remote_data": {"L": file.remote_data or []},
        }

        self.put_item(DYNAMODB_FILE_TABLE, new_file)

    def remove_file(self, file_id: str) -> None:
        key = get_file_key(file_id)
        self.delete_item(DYNAMODB_FILE_TABLE, key)
