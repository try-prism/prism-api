import logging
import time
import uuid
from http import HTTPStatus

from botocore.exceptions import ClientError
from constants import DYNAMODB_ORGANIZATION_TABLE
from exceptions import PrismDBException, PrismException
from fastapi import APIRouter
from models import get_organization_key
from models.RequestModels import (
    CancelInviteUserOrganizationRequest,
    InviteUserOrganizationRequest,
    RegisterOrganizationRequest,
    RemoveOrganizationRequest,
    UpdateOrganizationRequest,
)
from models.ResponseModels import (
    CancelInviteUserOrganizationResponse,
    ErrorDTO,
    GetOrganizationResponse,
    InviteUserOrganizationResponse,
    RegisterOrganizationResponse,
    RemoveOrganizationResponse,
    UpdateOrganizationResponse,
)
from pipeline import DataIndexingService
from services import CognitoService, SESService
from storage import DynamoDBService

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint                             | Description                            | Method |
|--------------------------------------|----------------------------------------|--------|
| `/organization`                      | Register a new organization            | POST   |
| `/organization`                      | Delete an organization                 | DELETE |
| `/organization/{org_id}`             | Retrieve an organization's details     | GET    |
| `/organization/{org_id}`             | Update an organization's admin id      | PATCH  |
| `/organization/{org_id}/invite`      | Invite an user to a organization       | POST   |
| `/organization/{org_id}/invite`      | Candel pending user invite             | DELETE |
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
        or not register_request.organization_email
        or not register_request.organization_admin_id
    ):
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid RegisterOrganizationRequest",
        )

    org_id = str(uuid.uuid4())
    logger.info("register_request=%s, org_id=%s", register_request, org_id)

    dynamodb_service = DynamoDBService()

    try:
        dynamodb_service.register_organization(
            org_id=org_id,
            org_name=register_request.organization_name,
            org_email=register_request.organization_email,
            org_admin_id=register_request.organization_admin_id,
        )
    except PrismDBException as e:
        logger.error("register_request=%s, error=%s", register_request, e)
        return ErrorDTO(
            code=e.code,
            description=e.message,
        )

    return RegisterOrganizationResponse(status=HTTPStatus.OK.value)


@router.delete(
    "/organization",
    summary="Remove an organization",
    tags=["Organization"],
    response_model=RemoveOrganizationResponse,
    responses={
        200: {"model": RemoveOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def remove_organization(
    remove_request: RemoveOrganizationRequest,
):
    if not remove_request.organization_id or not remove_request.organization_admin_id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid RemoveOrganizationRequest",
        )

    logger.info("remove_request=%s", remove_request)

    dynamodb_service = DynamoDBService()
    cognito_service = CognitoService()
    data_index_service = DataIndexingService(org_id=remove_request.organization_id)

    try:
        organization = dynamodb_service.get_organization(
            org_id=remove_request.organization_id
        )

        # Remove file data from the database
        dynamodb_service.remove_file_in_batch(organization.document_list)

        # Remove users
        for id in organization.user_list:
            dynamodb_service.remove_user(user_id=id, org_admin_id=organization.admin_id)
            cognito_service.remove_user(user_id=id)

        # Drop collection from the vector store
        data_index_service.drop_collection()

        response = dynamodb_service.remove_organization(
            org_id=remove_request.organization_id,
            org_admin_id=remove_request.organization_admin_id,
        )
    except Exception as e:
        logger.error("remove_request=%s, error=%s", remove_request, e)

        if isinstance(e, PrismDBException):
            return ErrorDTO(code=e.code, message=e.message)

        return ErrorDTO(
            code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            description="Internal server error",
        )

    logger.info("remove_request=%s, response=%s", remove_request, response)

    return RemoveOrganizationResponse(status=HTTPStatus.OK.value)


@router.get(
    "/organization/{org_id}",
    summary="Retrieve an organization's details",
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

    try:
        organization = dynamodb_service.get_organization(org_id)
    except PrismDBException as e:
        logger.error("org_id=%s, error=%s", org_id, e)
        return ErrorDTO(code=e.code, description=e.message)

    return GetOrganizationResponse(
        status=HTTPStatus.OK.value,
        organization=organization,
    )


@router.patch(
    "/organization/{org_id}",
    summary="Update an organization's admin id",
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

    try:
        organization = dynamodb_service.get_organization(org_id)
    except PrismDBException as e:
        logger.error("org_id=%s, update_request=%s error=%s", org_id, update_request, e)
        return ErrorDTO(code=e.code, description=e.message)

    timestamp = str(time.time())

    if organization.admin_id != update_request.prev_organization_admin_id:
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
            Key=get_organization_key(org_id),
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


@router.post(
    "/organization/{org_id}/invite",
    summary="Invite an user to a organization",
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
    ses_serivce = SESService()
    org_user_id = str(uuid.uuid4())

    try:
        dynamodb_service.modify_invited_users_list(
            org_id=org_id, org_user_id=org_user_id, is_remove=False
        )
        dynamodb_service.modify_whitelist(
            org_id=org_id,
            org_name=invite_request.organization_name,
            org_user_id=org_user_id,
            is_remove=False,
        )
        ses_serivce.send_signup_email(
            org_name=invite_request.organization_name,
            org_user_email=invite_request.organization_user_email,
            org_user_id=org_user_id,
        )
    except PrismException as e:
        logger.error(
            "org_id=%s, invite_request=%s, error=%s", org_id, invite_request, e
        )
        return ErrorDTO(code=e.code, message=e.message)

    return InviteUserOrganizationResponse(status=HTTPStatus.OK.value)


@router.delete(
    "/organization/{org_id}/invite",
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

    try:
        dynamodb_service.modify_invited_users_list(
            org_id=cancel_request.organization_user_id,
            org_user_id=cancel_request.organization_user_id,
            is_remove=True,
        )
        dynamodb_service.modify_whitelist(
            org_id=org_id,
            org_name=cancel_request.organization_name,
            org_user_id=cancel_request.organization_user_id,
            is_remove=True,
        )
    except PrismDBException as e:
        logger.error(
            "org_id=%s, cancel_request=%s, error=%s", org_id, cancel_request, e
        )
        return ErrorDTO(code=e.code, message=e.message)

    return CancelInviteUserOrganizationResponse(status=HTTPStatus.OK.value)
