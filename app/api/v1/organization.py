import uuid
from http import HTTPStatus

from exceptions import PrismDBException, PrismException, PrismExceptionCode
from fastapi import APIRouter
from loguru import logger
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
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def register_organization(
    register_request: RegisterOrganizationRequest,
):
    if (
        not register_request.organization_name
        or not register_request.organization_email
        or not register_request.organization_admin_email
    ):
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid RegisterOrganizationRequest",
        )

    org_id = str(uuid.uuid4()).replace("-", "_")
    logger.info("register_request={}, org_id={}", register_request, org_id)

    dynamodb_service = DynamoDBService()

    try:
        dynamodb_service.register_organization(
            org_id=org_id,
            org_name=register_request.organization_name,
            org_email=register_request.organization_email,
            org_admin_id=register_request.organization_admin_email,
        )

        response = await invite_user_to_organization(
            org_id=org_id,
            invite_request=InviteUserOrganizationRequest(
                organization_name=register_request.organization_name,
                organization_user_email=register_request.organization_email,
                organization_admin_id=register_request.organization_admin_email,
            ),
        )

        dynamodb_service.change_org_admin(
            org_id=org_id,
            original_admin_id=register_request.organization_admin_email,
            new_admin_id=response.org_user_id,
        )
    except PrismDBException as e:
        logger.error("register_request={}, error={}", register_request, e)
        raise

    return RegisterOrganizationResponse(status=HTTPStatus.OK.value)


@router.delete(
    "/organization",
    summary="Remove an organization",
    tags=["Organization"],
    response_model=RemoveOrganizationResponse,
    responses={
        200: {"model": RemoveOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def remove_organization(
    remove_request: RemoveOrganizationRequest,
):
    if not remove_request.organization_id or not remove_request.organization_admin_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid RemoveOrganizationRequest",
        )

    logger.info("remove_request={}", remove_request)

    dynamodb_service = DynamoDBService()
    cognito_service = CognitoService()
    data_index_service = DataIndexingService(org_id=remove_request.organization_id)

    try:
        organization = dynamodb_service.get_organization(
            org_id=remove_request.organization_id
        )

        # Remove file data from the database
        dynamodb_service.modify_file_in_batch(
            file_ids=organization.document_list, is_remove=True
        )

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
        logger.error("remove_request={}, error={}", remove_request, e)

        if isinstance(e, PrismDBException):
            raise

        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Service unavailable",
        )

    logger.info("remove_request={}, response={}", remove_request, response)

    return RemoveOrganizationResponse(status=HTTPStatus.OK.value)


@router.get(
    "/organization/{org_id}",
    summary="Retrieve an organization's details",
    tags=["Organization"],
    response_model=GetOrganizationResponse,
    responses={
        200: {"model": GetOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_organization(
    org_id: str,
):
    if not org_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid organization ID",
        )

    logger.info("org_id={}", org_id)

    dynamodb_service = DynamoDBService()

    try:
        organization = dynamodb_service.get_organization(org_id)
    except PrismDBException as e:
        logger.error("org_id={}, error={}", org_id, e)
        raise

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
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def update_organization(org_id: str, update_request: UpdateOrganizationRequest):
    if (
        not org_id
        or not update_request.new_organization_admin_id
        or not update_request.prev_organization_admin_id
    ):
        logger.error(
            "org_id={}, update_request={}, error=Invalid organization update request",
            org_id,
            update_request,
        )
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid organization update request",
        )

    logger.info("org_id={}, update_request={}", org_id, update_request)

    dynamodb_service = DynamoDBService()

    try:
        dynamodb_service.change_org_admin(
            org_id=org_id,
            original_admin_id=update_request.prev_organization_admin_id,
            new_admin_id=update_request.new_organization_admin_id,
        )
    except PrismDBException as e:
        logger.error(
            "org_id={}, update_request={}, error={}", org_id, update_request, e
        )
        raise

    return UpdateOrganizationResponse(status=HTTPStatus.OK.value)


@router.post(
    "/organization/{org_id}/invite",
    summary="Invite an user to a organization",
    tags=["Organization"],
    response_model=InviteUserOrganizationResponse,
    responses={
        200: {"model": InviteUserOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def invite_user_to_organization(
    org_id: str, invite_request: InviteUserOrganizationRequest
):
    if (
        not org_id
        or not invite_request.organization_name
        or not invite_request.organization_user_email
        or not invite_request.organization_admin_id
    ):
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid organization invite request",
        )

    logger.info("org_id={}, invite_request={}", org_id, invite_request)

    dynamodb_service = DynamoDBService()
    ses_serivce = SESService()
    org_user_id = str(uuid.uuid4())

    try:
        dynamodb_service.modify_invited_users_list(
            org_id=org_id,
            org_user_id=org_user_id,
            org_admin_id=invite_request.organization_admin_id,
            is_remove=False,
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
            "org_id={}, invite_request={}, error={}", org_id, invite_request, e
        )
        raise

    return InviteUserOrganizationResponse(
        status=HTTPStatus.OK.value, org_user_id=org_user_id
    )


@router.delete(
    "/organization/{org_id}/invite",
    summary="Candel pending user invite",
    tags=["Organization"],
    response_model=CancelInviteUserOrganizationResponse,
    responses={
        200: {"model": CancelInviteUserOrganizationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
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
        or not cancel_request.organization_admin_id
    ):
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid user invite cancel request",
        )

    logger.info("org_id={}, cancel_request={}", org_id, cancel_request)

    dynamodb_service = DynamoDBService()

    try:
        dynamodb_service.modify_invited_users_list(
            org_id=org_id,
            org_user_id=cancel_request.organization_user_id,
            org_admin_id=cancel_request.organization_admin_id,
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
            "org_id={}, cancel_request={}, error={}", org_id, cancel_request, e
        )
        raise

    return CancelInviteUserOrganizationResponse(status=HTTPStatus.OK.value)
