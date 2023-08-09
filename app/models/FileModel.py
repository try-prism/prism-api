from merge.resources.filestorage.types import File


def to_file_model(response: dict) -> File:
    item: dict = response["Item"]

    return File(
        id=item.get("id", {"S": ""})["S"],
        remote_id=item.get("remote_id", {"S": ""})["S"],
        name=item.get("name", {"S": ""})["S"],
        file_url=item.get("file_url", {"S": ""})["S"],
        file_thumbnail_url=item.get("file_thumbnail_url", {"S": ""})["S"],
        size=item.get("size", {"N": 0})["N"],
        mime_type=item.get("mime_type", {"S": ""})["S"],
        description=item.get("description", {"S": ""})["S"],
        folder=item.get("folder", {"S": ""})["S"],
        permissions=item.get("permissions", {"L": []})["L"],
        drive=item.get("drive", {"S": ""})["S"],
        remote_created_at=item.get("remote_created_at", {"S": ""})["S"],
        remote_updated_at=item.get("remote_updated_at", {"S": ""})["S"],
        remote_was_deleted=item.get("remote_was_deleted", {"BOOL": False})["BOOL"],
        modified_at=item.get("modified_at", {"S": ""})["S"],
        field_mappings=item.get("field_mappings", {"M": {}})["M"],
        remote_data=item.get("remote_data", {"L": []})["L"],
    )


def get_file_key(file_id: str) -> dict:
    return {"id": {"S": file_id}}
