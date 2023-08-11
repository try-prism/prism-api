from pydantic import BaseModel
from utils import deserialize


class WhitelistModel(BaseModel):
    id: str
    org_name: str
    org_id: str
    created_at: str


def to_whitelist_model(response: dict) -> WhitelistModel:
    item = deserialize(response["Item"])

    return WhitelistModel(
        id=item.get("id", ""),
        org_name=item.get("org_name", ""),
        org_id=item.get("org_id", ""),
        created_at=item.get("created_at", ""),
    )
