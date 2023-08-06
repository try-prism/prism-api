from pydantic import BaseModel


class WhitelistModel(BaseModel):
    id: str
    org_name: str
    org_id: str
    created_at: str


def to_whitelist_model(response: dict) -> WhitelistModel:
    item: dict = response["Item"]

    return WhitelistModel(
        id=item.get("id", {"S": ""})["S"],
        org_name=item.get("org_name", {"S": ""})["S"],
        org_id=item.get("org_id", {"S": ""})["S"],
        created_at=item.get("created_at", {"S": ""})["S"],
    )
