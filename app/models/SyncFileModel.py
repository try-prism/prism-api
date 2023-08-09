from enums import FileOperation
from pydantic import BaseModel


class SyncFileModel(BaseModel):
    id: str
    operation: FileOperation


def to_sync_file_model(response: dict) -> SyncFileModel:
    return SyncFileModel(
        id=response.get("id", {"S": ""})["S"],
        operation=FileOperation(response.get("operation", {"S": "UPDATED"})["S"]),
    )
