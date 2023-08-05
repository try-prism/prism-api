from pydantic import BaseModel

from .OrganizationModel import OrganizationModel
from .UserModel import UserModel
from .WhitelistModel import WhitelistModel


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


class RegisterUserResponse(BaseModel):
    status: int


class GetUserResponse(BaseModel):
    status: int
    user: UserModel


class GetInvitationResponse(BaseModel):
    status: int
    invitation: WhitelistModel
