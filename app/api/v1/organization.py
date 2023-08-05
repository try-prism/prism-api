import logging
import time
import uuid
from http import HTTPStatus

from botocore.exceptions import ClientError
from constants import DYNAMODB_ORGANIZATION_TABLE
from fastapi import APIRouter
from models import to_organization_model
from models.RequestModels import RegisterOrganizationRequest, UpdateOrganizationRequest
from models.ResponseModels import (
    ErrorDTO,
    GetOrganizationResponse,
    RegisterOrganizationResponse,
    UpdateOrganizationResponse,
)
from storage import DynamoDBService

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint                             | Description                           | Method |
|--------------------------------------|---------------------------------------|--------|
| `/organization`                      | Register a new organization           | POST   |
| `/organization/{id}`                 | Retrieve a organization's details     | GET    |
| `/organization/{id}`                 | Update a organization's admin id      | PATCH  |
| `/organization/{id}/user`            | Retrieve users of a organization      | GET    |
| `/organization/{id}/user`            | Invite a user to a organization       | POST   |
| `/organization/{id}/document`        | Retrieve documents of a organization  | GET    |
"""


@router.post(
    "/organization",
    summary="Register a new organization",
    tags=["Organization"],
    response_model=RegisterOrganizationResponse,
    responses={
        200: {"model": RegisterOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def register_organization(
    register_request: RegisterOrganizationRequest,
):
    if (
        not register_request.organization_name
        or not register_request.organization_admin_id
    ):
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid RegisterOrganizationRequest",
        )

    org_id = str(uuid.uuid4())
    logger.info(f"register_request={register_request}, org_id={org_id}")

    dynamodb_service = DynamoDBService()

    response = dynamodb_service.register_organization(
        org_id=org_id,
        org_name=register_request.organization_name,
        org_admin_id=register_request.organization_admin_id,
    )

    if not response:
        return ErrorDTO(
            code=HTTPStatus.FORBIDDEN.value,
            description="Failed to register organization",
        )

    return RegisterOrganizationResponse(status=HTTPStatus.OK.value)


@router.get(
    "/organization/{org_id}",
    summary="Retrieve a organization's details",
    tags=["Organization"],
    response_model=GetOrganizationResponse,
    responses={
        200: {"model": GetOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def get_organization(
    org_id: str,
):
    if not org_id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid organization ID",
        )

    logger.info(f"org_id={org_id}")

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_organization(org_id)

    if not response:
        return ErrorDTO(
            code=HTTPStatus.FORBIDDEN.value,
            description="Organization does not exist",
        )

    return GetOrganizationResponse(
        status=HTTPStatus.OK.value,
        organization=to_organization_model(response),
    )


@router.patch(
    "/organization/{org_id}",
    summary="Update a organization's admin id",
    tags=["Organization"],
    response_model=UpdateOrganizationResponse,
    responses={
        200: {"model": UpdateOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def update_organization(org_id: str, update_request: UpdateOrganizationRequest):
    if not org_id or not update_request.organization_admin_id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid organization update request",
        )

    logger.info(f"org_id={org_id}, update_request={update_request}")

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_organization(org_id)
    timestamp = str(time.time())

    if not response:
        return ErrorDTO(
            code=HTTPStatus.FORBIDDEN.value,
            description="Organization does not exist",
        )

    org = to_organization_model(response)
    if org.admin_id != update_request.prev_organization_admin_id:
        return ErrorDTO(
            code=HTTPStatus.FORBIDDEN.value,
            description="You don't have permission to edit this organization",
        )

    try:
        dynamodb_service.get_client().update_item(
            TableName=DYNAMODB_ORGANIZATION_TABLE,
            Key={"id": {"S": org_id}},
            UpdateExpression="SET admin_id = :id, updated_at = :ua",
            ExpressionAttributeValues={
                ":id": {"M": org_id},
                ":ua": {"S": timestamp},
            },
        )
    except ClientError as e:
        logger.error(str(e))
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description=str(e),
        )

    return UpdateOrganizationResponse(status=HTTPStatus.OK.value)
