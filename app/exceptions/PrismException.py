from abc import abstractmethod
from enum import Enum


class PrismException(Exception):
    def __init__(self, code: Enum, message: str):
        self.code = code
        self.message = message

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass
