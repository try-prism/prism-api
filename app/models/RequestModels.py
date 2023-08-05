from pydantic import BaseModel


class GenerateLinkTokenRequest(BaseModel):
    organization_id: str
    organization_name: str
    email_address: str


class IntegrationRequest(BaseModel):
    public_token: str
    organization_id: str
    organization_name: str
    email_address: str


class RegisterOrganizationRequest(BaseModel):
    organization_name: str
    organization_admin_id: str


class RemoveOrganizationRequest(BaseModel):
    organization_id: str
    organization_admin_id: str


class UpdateOrganizationRequest(BaseModel):
    organization_admin_id: str
    prev_organization_admin_id: str


class InviteUserOrganizationRequest(BaseModel):
    organization_name: str
    organization_user_email: str


class CancelInviteUserOrganizationRequest(BaseModel):
    organization_name: str
    organization_user_id: str
