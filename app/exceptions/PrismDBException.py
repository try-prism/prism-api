from enum import Enum

from .PrismException import PrismException


class PrismDBExceptionCode(Enum):
    ITEM_PUT_ERROR = 4001
    ITEM_UPDATE_ERROR = 4002
    ITEM_BATCH_GET_ERROR = 4003
    ITEM_DOES_NOT_EXIST = 4004
    USER_DOES_NOT_EXIST = 4005

    USER_NOT_INVITED = 4101
    USER_ALREADY_INVITED = 4102

    NOT_ENOUGH_PERMISSION = 4201

    VECTOR_STORE_FAILURE = 4301


class PrismDBException(PrismException):
    def __init__(self, code: PrismDBExceptionCode, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return f"PrismDBException: [{self.code.value}] {self.code.name}: {self.message}"

    def __repr__(self):
        return f"PrismDBException: [{self.code.value}] {self.code.name}: {self.message}"
