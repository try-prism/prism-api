from pydantic import BaseModel
from utils import deserialize


class OrganizationModel(BaseModel):
    id: str
    name: str
    email: str
    admin_id: str
    admin_email: str
    user_list: list[str]
    invited_user_list: list[str]
    link_id_map: dict
    document_list: list[str]
    created_at: str
    updated_at: str


def to_organization_model(response: dict) -> OrganizationModel:
    item = deserialize(response["Item"])

    return OrganizationModel(
        id=item.get("id", ""),
        name=item.get("name", ""),
        email=item.get("email", ""),
        admin_id=item.get("admin_id", ""),
        admin_email=item.get("admin_email", ""),
        user_list=item.get("user_list", []),
        invited_user_list=item.get("invited_user_list", []),
        link_id_map=item.get("link_id_map", {}),
        document_list=item.get("document_list", []),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )


def get_organization_key(org_id: str) -> dict:
    return {"id": {"S": org_id}}
