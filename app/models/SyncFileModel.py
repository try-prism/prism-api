from enums import FileOperation
from pydantic import BaseModel
from utils import deserialize


class SyncFileModel(BaseModel):
    id: str
    operation: FileOperation


def to_sync_file_model(response: dict) -> SyncFileModel:
    item = deserialize(response)

    return SyncFileModel(
        id=item.get("id", ""),
        operation=FileOperation(
            response.get("operation", FileOperation.UPDATED.value),
        ),
    )
