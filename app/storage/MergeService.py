import io
import logging
import uuid
from typing import Optional, Union

from constants import MERGE_API_KEY
from merge.client import Merge
from merge.resources.filestorage.types import CategoriesEnum, PaginatedFileList

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

    def list_files(self, next: Optional[str] = None) -> Union[PaginatedFileList, None]:
        if not self.account_token:
            logger.error("Invalid account token")
            return

        try:
            file_list = self.client.filestorage.files.list(cursor=next)
        except Exception as e:
            logger.error(str(e))
            return None

        return file_list

    def download_file(
        self, file_id: str, in_bytes: Optional[bool] = False
    ) -> Union[bytes, str, None]:
        if not self.account_token:
            logger.error("Invalid account token")
            return

        try:
            response = self.client.filestorage.files.download_retrieve(id=file_id)
        except Exception as e:
            logger.error(str(e))
            return None

        if in_bytes:
            return io.BytesIO(response)

        tmp_uuid = str(uuid.uuid4())

        with open(tmp_uuid, "wb") as f:
            for chunk in response:
                f.write(chunk)

        return tmp_uuid
