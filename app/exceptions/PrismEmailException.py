from enum import Enum

from .PrismException import PrismException


class PrismEmailExceptionCode(Enum):
    SIGNUP_EMAIL_NOT_SENT = 4001
    TEMP_PW_EMAIL_NOT_SENT = 4002


class PrismEmailException(PrismException):
    def __init__(self, code: PrismEmailExceptionCode, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return (
            f"PrismEmailException: [{self.code.value}] {self.code.name}: {self.message}"
        )

    def __repr__(self):
        return (
            f"PrismEmailException: [{self.code.value}] {self.code.name}: {self.message}"
        )
