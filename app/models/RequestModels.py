from pydantic import BaseModel

from .SyncFileModel import SyncFileModel


class IntegrationRequest(BaseModel):
    public_token: str
    organization_id: str
    organization_name: str
    organization_admin_id: str


class IntegrationRemoveRequest(BaseModel):
    organization_admin_id: str


class RegisterOrganizationRequest(BaseModel):
    organization_name: str
    organization_email: str
    organization_admin_email: str


class RemoveOrganizationRequest(BaseModel):
    organization_id: str
    organization_admin_id: str


class UpdateOrganizationRequest(BaseModel):
    new_organization_admin_id: str
    prev_organization_admin_id: str


class InviteUserOrganizationRequest(BaseModel):
    organization_name: str
    organization_user_email: str
    organization_admin_id: str


class CancelInviteUserOrganizationRequest(BaseModel):
    organization_name: str
    organization_user_id: str
    organization_admin_id: str


class GetUsersRequest(BaseModel):
    user_ids: list[str]


class RegisterUserRequest(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str


class SyncOrganizationDataRequest(BaseModel):
    account_token: str
    files: list[SyncFileModel]
