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
