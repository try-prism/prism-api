from pydantic import BaseModel


class AccessControlModel(BaseModel):
    id: str
    permissions: str
    created_at: str
    updated_at: str


def to_access_control_model(response: dict) -> AccessControlModel:
    return AccessControlModel(
        id=response.get("id", {"S": ""})["S"],
        permissions=response.get("permissions", {"L": []})["L"],
        created_at=response.get("created_at", {"S": ""})["S"],
        updated_at=response.get("updated_at", {"S": ""})["S"],
    )
