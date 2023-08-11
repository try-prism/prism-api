from pydantic import BaseModel
from utils import deserialize

from .AccessControlModel import AccessControlModel, to_access_control_model


class UserModel(BaseModel):
    id: str
    email: str
    name: str
    organization_id: str
    access_control: AccessControlModel
    created_at: str
    updated_at: str


def to_user_model(response: dict) -> UserModel:
    item = deserialize(response["Item"])

    return UserModel(
        id=item.get("id", ""),
        email=item.get("email", ""),
        name=item.get("name", ""),
        organization_id=item.get("organization_id", ""),
        access_control=to_access_control_model(item.get("access_control", {})),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )


def get_user_key(user_id: str) -> dict:
    return {"id": {"S": user_id}}
