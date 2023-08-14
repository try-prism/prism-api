import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from constants import (
    DYNAMODB_FILE_TABLE,
    DYNAMODB_ORGANIZATION_TABLE,
    DYNAMODB_USER_TABLE,
    DYNAMODB_WHITELIST_TABLE,
)
from enums import IntegrationStatus
from exceptions import PrismDBException, PrismDBExceptionCode
from loguru import logger
from merge.resources.filestorage.types import File
from models import (
    OrganizationModel,
    UserModel,
    WhitelistModel,
    get_organization_key,
    get_user_key,
    get_whitelist_key,
    to_organization_model,
    to_user_model,
    to_whitelist_model,
)
from utils import serialize

from .MergeService import MergeService


def exponential_backoff(func):
    def wrapper(*args, **kwargs):
        retry_count = 0
        while True:
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                if (
                    e.response["Error"]["Code"]
                    == "ProvisionedThroughputExceededException"
                ):
                    if retry_count == 5:
                        raise
                    retry_count += 1
                    time.sleep(2**retry_count)
                else:
                    raise

    return wrapper


class DynamoDBService:
    """
    Handles all of the operations related to DynamoDB.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html

    Author: Hwuiwon Kim (hwuiwon.kim@gmail.com)
    """

    def __init__(self):
        self.client = boto3.client("dynamodb")
        self.resource = boto3.resource("dynamodb")

    def put_item(self, table_name: str, item: dict) -> None:
        try:
            self.client.put_item(
                Item=item,
                TableName=table_name,
            )
        except ClientError as e:
            logger.error("table_name={}, item={}, error={}", table_name, item, str(e))
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

    def delete_item(self, table_name: str, key: dict) -> dict:
        response = self.client.delete_item(
            TableName=table_name, Key=key, ReturnValues="ALL_OLD"
        )

        # TODO: do we need this?
        if "Attributes" not in response:
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

    def batch_write(self, table_name: str, items: list[dict]) -> None:
        logger.info(
            "Running batch write. table_name={}, len(items)={}", table_name, len(items)
        )
        table = self.resource.Table(table_name)

        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)

    def batch_delete(self, table_name: str, keys: list[dict]) -> None:
        logger.info("Running batch delete. table_name={}, keys={}", table_name, keys)
        table = self.resource.Table(table_name)

        with table.batch_writer() as batch:
            for i in range(len(keys)):
                batch.delete_item(Key=keys[i])

    def parallel_batch_write(
        self, table_name: str, items: list[dict], is_remove: bool
    ) -> None:
        logger.info(
            "Running parallel batch write. table_name={}, is_remove={}",
            table_name,
            is_remove,
        )
        ops = self.batch_delete if is_remove else self.batch_write

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(ops, table_name, items[i : i + 100])
                for i in range(0, len(items), 100)
            ]

        for future in as_completed(futures):
            future.result()

    @exponential_backoff
    def optimized_batch_write(
        self, table_name: str, items: list, is_remove: bool
    ) -> None:
        logger.info(
            "Running optimized batch write. table_name={}, is_remove={}",
            table_name,
            is_remove,
        )
        self.parallel_batch_write(
            table_name=table_name, items=items, is_remove=is_remove
        )

    def register_organization(
        self, org_id: str, org_name: str, org_email: str, org_admin_id: str
    ) -> None:
        timestamp = str(time.time())
        new_organization = {
            "id": {"S": org_id},
            "name": {"S": org_name},
            "email": {"S": org_email},
            "admin_id": {"S": org_admin_id},
            "user_list": {"L": []},
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
                    table_name=DYNAMODB_WHITELIST_TABLE,
                    key=get_whitelist_key(org_user_id),
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
            self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))
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
            # "access_control": {"M": {}},
            "created_at": {"S": timestamp},
            "updated_at": {"S": timestamp},
        }

        self.put_item(DYNAMODB_USER_TABLE, new_user)
        organization = self.get_organization(organization_id)
        user_list = organization.user_list
        user_list.append(id)

        try:
            self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))
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
            self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))
        else:
            raise PrismDBException(
                code=PrismDBExceptionCode.USER_DOES_NOT_EXIST,
                message="User does not exist",
            )

    def add_integration(self, org_id: str, account_token: str) -> None:
        merge_service = MergeService(account_token=account_token)

        organization = self.get_organization(org_id)

        timestamp = str(time.time())
        link_id_map = organization.link_id_map

        integration_provider = merge_service.get_integration_provider()
        integration_item = integration_provider.dict()
        integration_item["created"] = timestamp
        integration_item["status"] = IntegrationStatus.SYNCING.value

        link_id_map[account_token] = integration_item

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))

    def remove_integration(self, org_id: str, account_token: str) -> None:
        organization = self.get_organization(org_id)

        link_id_map = organization.link_id_map
        del link_id_map[account_token]

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))

    def modify_integration_status(
        self, org_id: str, account_token: str, status: IntegrationStatus
    ) -> None:
        organization = self.get_organization(org_id)

        link_id_map = organization.link_id_map
        link_id_map[account_token]["status"] = status.value

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))

    def modify_organization_files(
        self, org_id: str, file_ids: list[str], is_remove: bool
    ) -> None:
        organization = self.get_organization(org_id)

        document_list = organization.document_list
        temp_file_set = set(document_list)

        if is_remove:
            temp_file_set.difference_update(file_ids)
        else:
            temp_file_set.update(file_ids)

        organization.document_list = list(temp_file_set)

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))

    def modify_file_in_batch(
        self,
        is_remove: bool,
        account_token: str | None = None,
        file_ids: list[str] | None = None,
        files: list[File] | None = None,
    ) -> None:
        if not is_remove and not account_token:
            raise PrismDBException(
                code=PrismDBExceptionCode.INVALID_ARGUMENT,
                message="account_token is required when adding files",
            )

        logger.info(
            "Modifying file(s). account_token: {}, is_remove={}",
            account_token,
            is_remove,
        )

        if is_remove:
            items = [{"id": file_id} for file_id in file_ids]
        else:
            items = []
            for file in files:
                new_file = file.dict()
                new_file["account_token"] = account_token
                del new_file["description"]
                del new_file["remote_data"]
                del new_file["remote_created_at"]
                del new_file["remote_updated_at"]
                new_file["modified_at"] = (
                    str(file.modified_at.timestamp()) if file.modified_at else ""
                )
                items.append(new_file)

        self.optimized_batch_write(
            table_name=DYNAMODB_FILE_TABLE, items=items, is_remove=is_remove
        )

        logger.info(
            "Finished modifying. account_token: {}, is_remove={}",
            account_token,
            is_remove,
        )

    def get_all_file_ids_for_integration(self, account_token: str) -> list[str]:
        logger.info("account_token: {}", account_token)

        ids = []
        table = self.resource.Table(DYNAMODB_FILE_TABLE)

        try:
            response = table.query(
                Select="SPECIFIC_ATTRIBUTES",
                AttributesToGet=["id"],
                KeyConditionExpression=Key("account_token").eq(account_token),
            )
            ids.extend(response["Items"])

            while "LastEvaluatedKey" in response:
                response = table.query(
                    Select="SPECIFIC_ATTRIBUTES",
                    AttributesToGet=["id"],
                    KeyConditionExpression=Key("account_token").eq(account_token),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                ids.extend(response["Items"])
        except ClientError as e:
            logger.error("account_token: {}, error={}", account_token, str(e))
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_BATCH_GET_ERROR,
                message="Failed to retrieve all file ids related to the integration",
            )

        cleaned_ids = [i["id"]["S"] for i in ids]
        return cleaned_ids

    def change_org_admin(self, org_id: str, new_admin_id: str) -> None:
        logger.info("org_id={}, new_admin_id={}", org_id, new_admin_id)

        organization = self.get_organization(org_id)

        if organization.admin_id != new_admin_id:
            logger.error(
                "org_id={}, new_admin_id={} error=no permission to edit this organization",
                org_id,
                new_admin_id,
            )
            raise PrismDBException(
                code=PrismDBExceptionCode.NOT_ENOUGH_PERMISSION,
                message="You don't have permission to edit this organization",
            )

        organization.admin_id = new_admin_id

        self.put_item(DYNAMODB_ORGANIZATION_TABLE, serialize(organization.dict()))
