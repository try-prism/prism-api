from .ExtendedEnum import ExtendedEnum


class IntegrationStatus(ExtendedEnum):
    SYNCING = "SYNCING"
    INDEXING = "INDEXING"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
