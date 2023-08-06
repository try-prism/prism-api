from abc import abstractmethod
from enum import Enum


class PrismException(Exception):
    @abstractmethod
    def __init__(self, code: Enum, message: str):
        pass

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass
