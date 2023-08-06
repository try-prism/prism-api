import io
import logging
import uuid
from typing import IO

from constants import MERGE_API_KEY, SUPPORTED_EXTENSIONS
from exceptions import PrismMergeException, PrismMergeExceptionCode
from merge.client import Merge
from merge.resources.filestorage.types import CategoriesEnum, File, PaginatedFileList

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

    def list_files(
        self, page_size: int | None = 50, next: str | None = None
    ) -> PaginatedFileList:
        if not self.account_token:
            logger.error("Invalid account token")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Invalid account token",
            )

        try:
            file_list = self.client.filestorage.files.list(
                page_size=page_size, cursor=next
            )
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
            logger.error("Invalid account token")
            raise PrismMergeException(
                code=PrismMergeExceptionCode.INVALID_ACCOUNT_TOKEN,
                message="Invalid account token",
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
