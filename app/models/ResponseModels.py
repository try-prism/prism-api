from pydantic import BaseModel

from .OrganizationModel import OrganizationModel
from .UserModel import UserModel
from .WhitelistModel import WhitelistModel


class ErrorDTO(BaseModel):
    code: int
    message: str


class GenerateLinkTokenResponse(BaseModel):
    status: int
    link_token: str


class IntegrationResponse(BaseModel):
    status: int
    integration_item: dict


class IntegrationDetailResponse(BaseModel):
    status: int
    integrations: dict


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


class GetUsersResponse(BaseModel):
    status: int
    users: list[UserModel]


class DeleteUserResponse(BaseModel):
    status: int


class GetInvitationResponse(BaseModel):
    status: int
    whitelist_user: WhitelistModel


class SyncOrganizationDataResponse(BaseModel):
    status: int
