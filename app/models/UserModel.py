from pydantic import BaseModel

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
    item: dict = response["Item"]

    return UserModel(
        id=item.get("id", {"S": ""})["S"],
        email=item.get("email", {"S": ""})["S"],
        name=item.get("name", {"S": ""})["S"],
        organization_id=item.get("organization_id", {"S": ""})["S"],
        access_control=to_access_control_model(
            item.get("access_control", {"M", {}})["M"]
        ),
        created_at=item.get("created_at", {"S": ""})["S"],
        updated_at=item.get("updated_at", {"S": ""})["S"],
    )


def get_user_key(user_id: str) -> dict:
    return {"id": {"S": user_id}}
