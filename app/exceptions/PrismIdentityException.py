from enum import Enum

from .PrismException import PrismException


class PrismIdentityExceptionCode(Enum):
    FAIL_CREATE_USER = 4001
    FAIL_DELETE_USER = 4002


class PrismIdentityException(PrismException):
    def __init__(self, code: PrismIdentityExceptionCode, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return f"PrismIdentityException: [{self.code.value}] {self.code.name}: {self.message}"

    def __repr__(self):
        return f"PrismIdentityException: [{self.code.value}] {self.code.name}: {self.message}"
