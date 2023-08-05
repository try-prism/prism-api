from pydantic import BaseModel


class OrganizationModel(BaseModel):
    id: str
    name: str
    admin_id: str
    user_list: list[str]
    index_id: str
    link_id_map: dict
    document_list: list[str]
    created_at: str
    updated_at: str


def to_organization_model(response: dict) -> OrganizationModel:
    item: dict = response["Item"]

    return OrganizationModel(
        id=item.get("id", {"S": ""})["S"],
        name=item.get("name", {"S": ""})["S"],
        admin_id=item.get("admin_id", {"S": ""})["S"],
        user_list=item.get("user_list", {"L": []})["L"],
        index_id=item.get("index_id", {"S": ""})["S"],
        link_id_map=item.get("link_id_map", {"M": {}})["M"],
        document_list=item.get("document_list", {"L": []})["L"],
        created_at=item.get("created_at", {"S": ""})["S"],
        updated_at=item.get("updated_at", {"S": ""})["S"],
    )
