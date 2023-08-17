import io
import time
import uuid
from typing import IO

from constants import MERGE_API_KEY, SUPPORTED_EXTENSIONS
from exceptions import PrismMergeException, PrismMergeExceptionCode
from loguru import logger
from merge.client import Merge
from merge.core.api_error import ApiError
from merge.resources.filestorage.types import (
    AccountDetails,
    CategoriesEnum,
    File,
    PaginatedFileList,
    PaginatedFolderList,
    SyncStatusStatusEnum,
)


class MergeService:
    """https://github.com/merge-api/merge-python-client"""

    def __init__(self, account_token: str | None = None):
        self.account_token = account_token
        self.client = Merge(api_key=MERGE_API_KEY, account_token=account_token)

    def generate_link_token(self, org_id: str, org_name: str, org_email: str) -> str:
        logger.info("org_id={}, org_name={}, org_email={}", org_id, org_name, org_email)

        try:
            link_token_response = self.client.filestorage.link_token.create(
                end_user_origin_id=str(uuid.uuid4()),
                end_user_organization_name=org_name,
                end_user_email_address=org_email,
                categories=[CategoriesEnum.FILESTORAGE],
            )
        except Exception as e:
            logger.error(
                "org_id={}, org_name={}, org_email={}, error={}",
                org_id,
                org_name,
                org_email,
                str(e),
            )
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_GENERATE_LINK_TOKEN,
                message="Could not generate link token",
            )

        return link_token_response.link_token

    def generate_account_token(self, public_token: str) -> str:
        logger.info("public_token={}", public_token)

        try:
            account_token_response = self.client.filestorage.account_token.retrieve(
                public_token=public_token
            )
        except Exception as e:
            logger.error("public_token={}, error={}", public_token, str(e))
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_GENERATE_ACCOUNT_TOKEN,
                message="Could not generate account token",
            )

        return account_token_response.account_token

    def get_integration_provider(self) -> AccountDetails:
        logger.info("account_token={}", self.account_token)

        if not self.account_token:
            logger.error("Account token can't be null")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Account token can't be null",
            )

        try:
            integration_provider = self.client.filestorage.account_details.retrieve()
        except Exception as e:
            logger.error("account_token={}, error={}", self.account_token, str(e))
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_FETCH_INTEGRATION_DETAILS,
                message="Could not get integration provider details",
            )

        return integration_provider

    def check_sync_status(self) -> bool:
        logger.info("account_token={}", self.account_token)

        if not self.account_token:
            logger.error("Account token can't be null")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Account token can't be null",
            )

        try:
            sync_status = self.client.filestorage.sync_status.list(page_size=100)
            results = sync_status.results

            if all(r.status == SyncStatusStatusEnum.DONE for r in results):
                return True

            if any(r.status == SyncStatusStatusEnum.FAILED for r in results):
                raise PrismMergeException(
                    code=PrismMergeExceptionCode.FAILED_TO_SYNC,
                    message="Failed to sync",
                )
        except Exception as e:
            logger.error("account_token={}, error={}", self.account_token, str(e))

            if isinstance(e, PrismMergeException):
                raise

            raise PrismMergeException(
                code=PrismMergeExceptionCode.UNKNOWN,
                message=str(e),
            )

        return False

    def list_folders_in_folder(
        self,
        folder_id: str | None = None,
        drive_id: str | None = None,
        next: str | None = None,
    ) -> PaginatedFolderList:
        if not self.account_token:
            logger.error("Account token can't be null")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Account token can't be null",
            )

        if not folder_id and not drive_id:
            logger.error(
                "account_token={}, folder_id={}, drive_id={}, next={}, error={}",
                self.account_token,
                folder_id,
                drive_id,
                next,
                "Either drive id or folder id is required",
            )
            raise PrismMergeException(
                code=PrismMergeExceptionCode.REQUIRES_DRIVE_ID,
                message="Either drive id or folder id is required",
            )

        logger.info(
            "account_token={}, folder_id={}, drive_id={}, next={}",
            self.account_token,
            folder_id,
            drive_id,
            next,
        )

        try:
            folder_list = self.client.filestorage.folders.list(
                page_size=100, folder_id=folder_id, drive_id=drive_id, cursor=next
            )
        except Exception as e:
            logger.error(
                "account_token={}, folder_id={}, drive_id={}, next={}, error={}",
                self.account_token,
                folder_id,
                drive_id,
                next,
                str(e),
            )
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_LIST_FOLDERS,
                message="Could not fetch folders",
            )

        return folder_list

    def list_all_files(self, next: str | None = None) -> PaginatedFileList:
        logger.info("account_token={}", self.account_token)

        if not self.account_token:
            logger.error("Account token can't be null")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Account token can't be null",
            )

        try:
            file_list = self.client.filestorage.files.list(page_size=100, cursor=next)
        except Exception as e:
            logger.error(
                "account_token={}, next={}, error={}", self.account_token, next, str(e)
            )
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_LIST_FILES,
                message="Could not fetch files",
            )

        return file_list

    def generate_file_list(self) -> list[File]:
        logger.info("account_token={}", self.account_token)

        file_list: list[File] = []
        response = self.list_all_files()

        file_list.extend(response.results)

        while response.next is not None:
            try:
                response = self.list_all_files(next=response.next)
                file_list.extend(response.results)
            except ApiError as e:
                logger.info(
                    "account_token={}, error={}, Too many requests. Waiting for 1 min to resume..",
                    self.account_token,
                    e,
                )
                time.sleep(60)

        return file_list

    def download_file(
        self, file: File, in_bytes: bool | None = False
    ) -> IO[bytes] | str:
        logger.info(
            "file_id={}, file_name={}, in_bytes={}", file.id, file.name, in_bytes
        )

        if not self.account_token:
            logger.error("Account token can't be null")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Account token can't be null",
            )

        file_extension = file.name.split(".")[-1]

        if file_extension not in SUPPORTED_EXTENSIONS:
            logger.error("File type not supported: .{}", file_extension)
            raise PrismMergeException(
                code=PrismMergeExceptionCode.FILE_TYPE_NOT_SUPPORTED,
                message="File type not supported",
            )

        try:
            response = self.client.filestorage.files.download_retrieve(id=file.id)
        except Exception as e:
            logger.error(
                "account_token={}, file_id={}, error={}",
                self.account_token,
                file.id,
                str(e),
            )
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_DOWNLOAD_FILE,
                message="Could not download file",
            )

        if in_bytes:
            return io.BytesIO(response)

        tmp_uuid = str(uuid.uuid4())

        with open(tmp_uuid, "wb") as f:
            for chunk in response:
                f.write(chunk)

        return tmp_uuid

    def remove_integration(self) -> None:
        try:
            self.client.filestorage.delete_account.delete()
        except Exception as e:
            logger.error("account_token={}, error={}", self.account_token, str(e))
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_DELETE_INTEGRATION,
                message="Could not delete integration",
            )
