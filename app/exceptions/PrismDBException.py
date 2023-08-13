from enum import Enum

from .PrismException import PrismException


class PrismDBExceptionCode(Enum):
    ITEM_PUT_ERROR = 4001
    ITEM_UPDATE_ERROR = 4002
    ITEM_BATCH_GET_ERROR = 4003
    ITEM_BATCH_PUT_ERROR = 4004
    ITEM_BATCH_PROCESS_ERROR = 4005
    ITEM_DOES_NOT_EXIST = 4006
    USER_DOES_NOT_EXIST = 4007

    USER_NOT_INVITED = 4101
    USER_ALREADY_INVITED = 4102

    NOT_ENOUGH_PERMISSION = 4201

    COULD_NOT_CONNECT_TO_VECTOR_STORE = 4301

    COULD_NOT_CREATE_TABLE = 4401

    INVALID_ARGUMENT = 4501


class PrismDBException(PrismException):
    def __init__(self, code: PrismDBExceptionCode, message: str):
        self.code = code
        self.message = message

    def __str__(self):
        return f"PrismDBException: [{self.code.value}] {self.code.name}: {self.message}"

    def __repr__(self):
        return f"PrismDBException: [{self.code.value}] {self.code.name}: {self.message}"
