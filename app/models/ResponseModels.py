from pydantic import BaseModel

from .OrganizationModel import OrganizationModel


class ErrorDTO(BaseModel):
    code: int
    description: str


class GenerateLinkTokenResponse(BaseModel):
    status: int
    link_token: str


class IntegrationResponse(BaseModel):
    status: int


class IntegrationDetailResponse(BaseModel):
    status: int
    integrations: list


class IntegrationRemoveResponse(BaseModel):
    status: int


class RegisterOrganizationResponse(BaseModel):
    status: int


class RemoveOrganizationResponse(BaseModel):
    status: int


class GetOrganizationResponse(BaseModel):
    status: int
    organization: OrganizationModel


class UpdateOrganizationResponse(BaseModel):
    status: int


class InviteUserOrganizationResponse(BaseModel):
    status: int


class CancelInviteUserOrganizationResponse(BaseModel):
    status: int
