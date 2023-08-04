import io
import logging
import uuid
from typing import IO, Optional, Union

from constants import MERGE_API_KEY, SUPPORTED_EXTENSIONS
from merge.client import Merge
from merge.resources.filestorage.types import CategoriesEnum, File, PaginatedFileList

logger = logging.getLogger(__name__)


class MergeService:
    """https://github.com/merge-api/merge-python-client"""

    def __init__(self, account_token: Optional[str] = None):
        self.client = Merge(api_key=MERGE_API_KEY, account_token=account_token)
        self.account_token = account_token

    def generate_link_token(
        self, org_id: str, org_name: str, org_email: str
    ) -> Union[str, None]:
        try:
            link_token_response = self.client.filestorage.link_token.create(
                end_user_origin_id=org_id,
                end_user_organization_name=org_name,
                end_user_email_address=org_email,
                categories=[CategoriesEnum.FILESTORAGE],
            )
        except Exception as e:
            logger.error(str(e))
            return None

        return link_token_response.link_token

    def generate_account_token(self, public_token: str) -> Union[str, None]:
        try:
            account_token_response = self.client.filestorage.account_token.retrieve(
                public_token=public_token
            )
        except Exception as e:
            logger.error(str(e))
            return None

        return account_token_response.account_token

    def list_files(
        self, page_size: Optional[int] = 50, next: Optional[str] = None
    ) -> Union[PaginatedFileList, None]:
        if not self.account_token:
            logger.error("Invalid account token")
            return

        try:
            file_list = self.client.filestorage.files.list(
                page_size=page_size, cursor=next
            )
        except Exception as e:
            logger.error(f"account_token={self.account_token}, next={next}, {str(e)}")
            return None

        return file_list

    def download_file(
        self, file: File, in_bytes: Optional[bool] = False
    ) -> Union[IO[bytes], str, None]:
        if not self.account_token:
            logger.error("Invalid account token")
            return

        file_extension = file.name.split(".")[-1]

        if file_extension not in SUPPORTED_EXTENSIONS:
            logger.error(f"File type not supported: .{file_extension}")
            return

        try:
            response = self.client.filestorage.files.download_retrieve(id=file.id)
        except Exception as e:
            logger.error(
                f"account_token={self.account_token}, file_id={file.id}, {str(e)}"
            )
            return None

        if in_bytes:
            return io.BytesIO(response)

        tmp_uuid = str(uuid.uuid4())

        with open(tmp_uuid, "wb") as f:
            for chunk in response:
                f.write(chunk)

        return tmp_uuid
