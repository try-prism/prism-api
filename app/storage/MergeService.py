import io
import logging
import uuid
from typing import IO

from constants import MERGE_API_KEY, SUPPORTED_EXTENSIONS
from exceptions import PrismMergeException, PrismMergeExceptionCode
from merge.client import Merge
from merge.resources.filestorage.types import (
    CategoriesEnum,
    File,
    PaginatedFileList,
    PaginatedFolderList,
    SyncStatusStatusEnum,
)

logger = logging.getLogger(__name__)


class MergeService:
    """https://github.com/merge-api/merge-python-client"""

    def __init__(self, account_token: str | None = None):
        self.client = Merge(api_key=MERGE_API_KEY, account_token=account_token)
        self.account_token = account_token

    def generate_link_token(self, org_id: str, org_name: str, org_email: str) -> str:
        try:
            link_token_response = self.client.filestorage.link_token.create(
                end_user_origin_id=org_id,
                end_user_organization_name=org_name,
                end_user_email_address=org_email,
                categories=[CategoriesEnum.FILESTORAGE],
            )
        except Exception as e:
            logger.error(
                "org_id=%s, org_name=%s, org_email=%s, error=%s",
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
        try:
            account_token_response = self.client.filestorage.account_token.retrieve(
                public_token=public_token
            )
        except Exception as e:
            logger.error("public_token=%s, error=%s", public_token, str(e))
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_GENERATE_ACCOUNT_TOKEN,
                message="Could not generate account token",
            )

        return account_token_response.account_token

    def check_sync_status(self) -> bool:
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
        except PrismMergeException as e:
            raise e
        except Exception as e:
            logger.error("account_token=%s, error=%s", self.account_token, e)
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
                "account_token=%s, folder_id=%s, drive_id=%s, next=%s, error=%s",
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

        try:
            folder_list = self.client.filestorage.folders.list(
                page_size=100, folder_id=folder_id, drive_id=drive_id, cursor=next
            )
        except Exception as e:
            logger.error(
                "account_token=%s, folder_id=%s, drive_id=%s, next=%s, error=%s",
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
                "account_token=%s, next=%s, error=%s", self.account_token, next, str(e)
            )
            raise PrismMergeException(
                code=PrismMergeExceptionCode.COULD_NOT_LIST_FILES,
                message="Could not fetch files",
            )

        return file_list

    def download_file(
        self, file: File, in_bytes: bool | None = False
    ) -> IO[bytes] | str:
        if not self.account_token:
            logger.error("Account token can't be null")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Account token can't be null",
            )

        file_extension = file.name.split(".")[-1]

        if file_extension not in SUPPORTED_EXTENSIONS:
            logger.error("File type not supported: .%s", file_extension)
            raise PrismMergeException(
                code=PrismMergeExceptionCode.FILE_TYPE_NOT_SUPPORTED,
                message="File type not supported",
            )

        try:
            response = self.client.filestorage.files.download_retrieve(id=file.id)
        except Exception as e:
            logger.error(
                "account_token=%s, file_id=%s, error=%s",
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
