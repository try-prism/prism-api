from merge.resources.filestorage.types import File
from utils import deserialize


def to_file_model(response: dict) -> File:
    item = deserialize(response["Item"])

    return File(
        id=item.get("id", ""),
        remote_id=item.get("remote_id", ""),
        name=item.get("name", ""),
        file_url=item.get("file_url", ""),
        file_thumbnail_url=item.get("file_thumbnail_url", ""),
        size=item.get("size", 0),
        mime_type=item.get("mime_type", ""),
        description=item.get("description", ""),
        folder=item.get("folder", ""),
        permissions=item.get("permissions", []),
        drive=item.get("drive", ""),
        remote_created_at=item.get("remote_created_at", ""),
        remote_updated_at=item.get("remote_updated_at", ""),
        remote_was_deleted=item.get("remote_was_deleted", False),
        modified_at=item.get("modified_at", ""),
        field_mappings=item.get("field_mappings", {}),
        remote_data=item.get("remote_data", []),
    )


def get_file_key(file_id: str) -> dict:
    return {"id": {"S": file_id}}
