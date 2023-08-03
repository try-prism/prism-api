from pydantic import BaseModel


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
