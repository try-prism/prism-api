from enum import Enum

from .PrismException import PrismException


class PrismMergeExceptionCode(Enum):
    COULD_NOT_GENERATE_LINK_TOKEN = 4001
    COULD_NOT_GENERATE_ACCOUNT_TOKEN = 4002
    COULD_NOT_LIST_FILES = 4003
    COULD_NOT_LIST_FOLDERS = 4004
    COULD_NOT_DOWNLOAD_FILE = 4005
    COULD_NOT_FETCH_SYNC_STATUS = 4006

    INVALID_ACCOUNT_TOKEN = 4101
    FILE_TYPE_NOT_SUPPORTED = 4102

    REQUIRES_DRIVE_ID = 4201
    REQUIRES_FOLDER_ID = 4202

    FAILED_TO_SYNC = 4301

    UNKNOWN = 5000


class PrismMergeException(PrismException):
    def __init__(self, code: PrismMergeExceptionCode, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return (
            f"PrismMergeException: [{self.code.value}] {self.code.name}: {self.message}"
        )

    def __repr__(self):
        return (
            f"PrismMergeException: [{self.code.value}] {self.code.name}: {self.message}"
        )
