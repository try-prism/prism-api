from pydantic import BaseModel


class AccessControlModel(BaseModel):
    id: str
    permissions: str
    created_at: str
    updated_at: str


def to_access_control_model(response: dict) -> AccessControlModel:
    item: dict = response.get("access_control", {"M", {}})["M"]

    return AccessControlModel(
        id=item.get("id", {"S": ""})["S"],
        permissions=item.get("permissions", {"L": []})["L"],
        created_at=item.get("created_at", {"S": ""})["S"],
        updated_at=item.get("updated_at", {"S": ""})["S"],
    )
