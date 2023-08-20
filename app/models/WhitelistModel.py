from pydantic import BaseModel
from utils import deserialize


class WhitelistModel(BaseModel):
    id: str
    org_name: str
    org_id: str
    org_user_email: str
    created_at: str


def to_whitelist_model(response: dict) -> WhitelistModel:
    item = deserialize(response["Item"])

    return WhitelistModel(
        id=item.get("id", ""),
        org_name=item.get("org_name", ""),
        org_id=item.get("org_id", ""),
        org_user_email=item.get("org_user_email", ""),
        created_at=item.get("created_at", ""),
    )


def get_whitelist_key(user_id: str) -> dict:
    return {"id": {"S": user_id}}
