import logging
import time
import uuid
from http import HTTPStatus

from botocore.exceptions import ClientError
from constants import DYNAMODB_ORGANIZATION_TABLE
from fastapi import APIRouter
from models import to_organization_model
from models.RequestModels import (
    CancelInviteUserOrganizationRequest,
    InviteUserOrganizationRequest,
    RegisterOrganizationRequest,
    UpdateOrganizationRequest,
)
from models.ResponseModels import (
    CancelInviteUserOrganizationResponse,
    ErrorDTO,
    GetOrganizationResponse,
    InviteUserOrganizationResponse,
    RegisterOrganizationResponse,
    UpdateOrganizationResponse,
)
from services import SESService
from storage import DynamoDBService

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint                             | Description                           | Method |
|--------------------------------------|---------------------------------------|--------|
| `/organization`                      | Register a new organization           | POST   |
| `/organization`                      | Delete an organization                | DELETE |
| `/organization/{org_id}`             | Retrieve a organization's details     | GET    |
| `/organization/{org_id}`             | Update a organization's admin id      | PATCH  |
| `/organization/{org_id}/user`        | Retrieve users of a organization      | GET    |
| `/organization/{org_id}/user`        | Invite a user to a organization       | POST   |
| `/organization/{org_id}/user`        | Candel pending user invite            | DELETE |
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
    logger.info("register_request=%s, org_id=%s", register_request, org_id)

    dynamodb_service = DynamoDBService()

    response = dynamodb_service.register_organization(
        org_id=org_id,
        org_name=register_request.organization_name,
        org_admin_id=register_request.organization_admin_id,
    )

    if not response:
        logger.error(
            "register_request=%s, error=Failed to register organization",
            register_request,
        )
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

    logger.info("org_id=%s", org_id)

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_organization(org_id)

    if not response:
        logger.error("org_id=%s, error=Organization does not exist", org_id)
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
    if (
        not org_id
        or not update_request.organization_admin_id
        or update_request.prev_organization_admin_id
    ):
        logger.error(
            "org_id=%s, update_request=%s, error=Invalid organization update request",
            org_id,
            update_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid organization update request",
        )

    logger.info("org_id=%s, update_request=%s", org_id, update_request)

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_organization(org_id)
    timestamp = str(time.time())

    if not response:
        logger.error(
            "org_id=%s, update_request=%s error=Organization does not exist",
            org_id,
            update_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Organization does not exist",
        )

    org = to_organization_model(response)
    if org.admin_id != update_request.prev_organization_admin_id:
        logger.error(
            "org_id=%s, update_request=%s error=no permission to edit this organization",
            org_id,
            update_request,
        )
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


@router.get(
    "/organization/{org_id}/user",
    summary="Retrieve users of a organization",
    tags=["Organization"],
    response_model=GetOrganizationResponse,
    responses={
        200: {"model": GetOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def get_organization_users(
    org_id: str,
):
    if not org_id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid organization ID",
        )

    logger.info("org_id=%s", org_id)

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_organization(org_id)

    if not response:
        logger.error("org_id=%s, error=Organization does not exist", org_id)
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Organization does not exist",
        )

    return GetOrganizationResponse(
        status=HTTPStatus.OK.value,
        organization=to_organization_model(response).user_list,
    )


@router.post(
    "/organization/{org_id}/user",
    summary="Invite a user to a organization",
    tags=["Organization"],
    response_model=InviteUserOrganizationResponse,
    responses={
        200: {"model": InviteUserOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def invite_user_to_organization(
    org_id: str, invite_request: InviteUserOrganizationRequest
):
    if (
        not org_id
        or not invite_request.organization_name
        or not invite_request.organization_user_email
    ):
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid organization invite request",
        )

    logger.info("org_id=%s, invite_request=%s", org_id, invite_request)

    dynamodb_service = DynamoDBService()
    org_user_id = str(uuid.uuid4())

    invited_response = dynamodb_service.modify_invited_users_list(
        org_id=org_id, org_user_id=org_user_id, is_remove=False
    )

    if not invited_response:
        logger.error(
            "org_id=%s, invite_request=%s, error=Org does not exist or user already invited",
            org_id,
            invite_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Organization does not exist or user has been already invited",
        )

    whitelist_response = dynamodb_service.modify_whitelist(
        org_id=org_id,
        org_name=invite_request.organization_name,
        org_user_id=org_user_id,
        is_remove=False,
    )

    if not whitelist_response:
        logger.error(
            "org_id=%s, invite_request=%s, error=Failed to add user to whitelist",
            org_id,
            invite_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Failed to add user to whitelist",
        )

    ses_serivce = SESService()
    response = ses_serivce.send_signup_email(
        org_name=invite_request.organization_name,
        org_user_email=invite_request.organization_user_email,
        org_user_id=org_user_id,
    )

    if not response:
        logger.error(
            "org_id=%s, invite_request=%s, error=Failed to send invitation email",
            org_id,
            invite_request,
        )
        return ErrorDTO(
            code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            description="Failed to send invitation email",
        )

    return InviteUserOrganizationResponse(status=HTTPStatus.OK.value)


@router.delete(
    "/organization/{org_id}/user",
    summary="Candel pending user invite",
    tags=["Organization"],
    response_model=CancelInviteUserOrganizationResponse,
    responses={
        200: {"model": CancelInviteUserOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def cancel_pending_user_invite(
    org_id: str,
    cancel_request: CancelInviteUserOrganizationRequest,
):
    if (
        not org_id
        or not cancel_request.organization_name
        or not cancel_request.organization_user_id
    ):
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid user invite cancel request",
        )

    logger.info("org_id=%s, cancel_request=%s", org_id, cancel_request)

    dynamodb_service = DynamoDBService()

    invited_response = dynamodb_service.modify_invited_users_list(
        org_id=cancel_request.organization_user_id,
        org_user_id=cancel_request.organization_user_id,
        is_remove=True,
    )

    if not invited_response:
        logger.error(
            "org_id=%s, cancel_request=%s, error=Org does not exist or user not invited",
            org_id,
            cancel_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Organization does not exist or user not invited",
        )

    whitelist_response = dynamodb_service.modify_whitelist(
        org_id=org_id,
        org_name=cancel_request.organization_name,
        org_user_id=cancel_request.organization_user_id,
        is_remove=True,
    )

    if not whitelist_response:
        logger.error(
            "org_id=%s, cancel_request=%s, error=Failed to remove user from whitelist",
            org_id,
            cancel_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Failed to remove user from whitelist",
        )

    return CancelInviteUserOrganizationResponse(status=HTTPStatus.OK.value)
