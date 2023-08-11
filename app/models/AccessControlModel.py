from pydantic import BaseModel
from utils import deserialize


class AccessControlModel(BaseModel):
    id: str
    permissions: str
    created_at: str
    updated_at: str


def to_access_control_model(response: dict) -> AccessControlModel:
    item = deserialize(response)

    return AccessControlModel(
        id=item.get("id", ""),
        permissions=item.get("permissions", []),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )
