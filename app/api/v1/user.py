from http import HTTPStatus

from constants import DYNAMODB_USER_TABLE
from exceptions import PrismDBException, PrismException, PrismExceptionCode
from fastapi import APIRouter, Header
from loguru import logger
from models import to_user_model
from models.RequestModels import (
    CancelInviteUserOrganizationRequest,
    GetUsersRequest,
    RegisterUserRequest,
)
from models.ResponseModels import (
    CheckAdminResponse,
    DeleteUserResponse,
    ErrorDTO,
    GetInvitationResponse,
    GetUserResponse,
    GetUsersResponse,
    RegisterUserResponse,
)
from services import CognitoService
from storage import DynamoDBService

from .organization import cancel_pending_user_invite

router = APIRouter()


"""
| Endpoint                       | Description                          | Method |
|--------------------------------|--------------------------------------|--------|
| `/user`                        | Register a new user                  | POST   |
| `/user/{user_id}`              | Retrieve a user's details            | GET    |
| `/user/{user_id}`              | Update a user's details (*)          | PATCH  |
| `/user/{user_id}`              | Delete a user's account              | DELETE |
| `/user/{user_id}/admin `       | Check if a user is an admin          | GET    |
| `/user/{user_id}/invitation`   | Get invitation data from whitelist   | GET    |
| `/users`                       | Get user data in batch               | GET    |
"""


@router.post(
    "/user",
    summary="Register a new user",
    tags=["User"],
    response_model=RegisterUserResponse,
    responses={
        200: {"model": RegisterUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def register_user(
    register_request: RegisterUserRequest,
):
    if (
        not register_request.id
        or not register_request.email
        or not register_request.first_name
        or not register_request.last_name
    ):
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid RegisterUserRequest",
        )

    logger.info("register_request={}", register_request)

    dynamodb_service = DynamoDBService()
    cognito_service = CognitoService()

    try:
        whitelist_user = dynamodb_service.get_whitelist_user_data(
            user_id=register_request.id
        )
        logger.info(
            "register_request={}, whitelist_user={}", register_request, whitelist_user
        )
        # Add user to the cognito user pool
        cognito_service.create_user(
            user_id=register_request.id,
            user_email=register_request.email,
            first_name=register_request.first_name,
            last_name=register_request.last_name,
            organization_id=whitelist_user.org_id,
        )
        # Add user to user table
        dynamodb_service.register_user(
            id=register_request.id,
            email=register_request.email,
            name=register_request.first_name + " " + register_request.last_name,
            organization_id=whitelist_user.org_id,
        )

        # Get org admin id to use for cancel pending user invite
        organization = dynamodb_service.get_organization(org_id=whitelist_user.org_id)
        organization_admin_id = organization.admin_id
    except PrismException as e:
        logger.error(
            "register_request={}, error={}",
            register_request,
            e,
        )
        raise

    await cancel_pending_user_invite(
        org_id=whitelist_user.org_id,
        cancel_request=CancelInviteUserOrganizationRequest(
            organization_name=whitelist_user.org_name,
            organization_user_id=whitelist_user.id,
            organization_admin_id=organization_admin_id,
        ),
    )

    return RegisterUserResponse(status=HTTPStatus.OK.value)


@router.get(
    "/user/{user_id}",
    summary="Retrieve a user's details",
    tags=["User"],
    response_model=GetUserResponse,
    responses={
        200: {"model": GetUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_user(user_id: str):
    if not user_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User id is required",
        )

    logger.info("user_id={}", user_id)

    dynamodb_service = DynamoDBService()

    try:
        user = dynamodb_service.get_user(user_id=user_id)
    except PrismDBException as e:
        logger.error("user_id={}, error={}", user_id, e)
        raise

    return GetUserResponse(status=HTTPStatus.OK.value, user=user)


@router.delete(
    "/user/{user_id}",
    summary="Delete a user's account",
    tags=["User"],
    response_model=DeleteUserResponse,
    responses={
        200: {"model": DeleteUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def delete_user(user_id: str, org_admin_id: str = Header()):
    if not user_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User id is required",
        )

    if user_id == org_admin_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="You cannot delete yourself",
        )

    logger.info("user_id={}, org_admin_id={}", user_id, org_admin_id)

    dynamodb_service = DynamoDBService()
    cognito_service = CognitoService()

    try:
        cognito_service.remove_user(user_id=user_id)
        dynamodb_service.remove_user(user_id=user_id, org_admin_id=org_admin_id)
    except PrismException as e:
        logger.error("user_id={}, org_admin_id={}, error={}", user_id, org_admin_id, e)
        raise

    return DeleteUserResponse(status=HTTPStatus.OK.value)


@router.get(
    "/user/{user_id}/admin",
    summary="Check if a user is an admin",
    tags=["User"],
    response_model=CheckAdminResponse,
    responses={
        200: {"model": CheckAdminResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def is_admin(user_id: str, organization_id: str = Header()):
    if not user_id or not organization_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User ID and organization ID is required",
        )

    logger.info("user_id={}, organization_id={}", user_id, organization_id)

    dynamodb_service = DynamoDBService()

    try:
        organization = dynamodb_service.get_organization(org_id=organization_id)
    except PrismDBException as e:
        logger.error(
            "user_id={}, organization_id={}, error={}", user_id, organization_id, e
        )
        raise

    return CheckAdminResponse(
        status=HTTPStatus.OK.value, is_admin=organization.admin_id != user_id
    )


@router.get(
    "/user/{user_id}/invitation",
    summary="Get invitation data from whitelist",
    tags=["User"],
    response_model=GetInvitationResponse,
    responses={
        200: {"model": GetInvitationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_invitation_data(user_id: str):
    if not user_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User id is required",
        )

    logger.info("user_id={}", user_id)

    dynamodb_service = DynamoDBService()

    try:
        whitelist_user = dynamodb_service.get_whitelist_user_data(user_id=user_id)
    except PrismDBException as e:
        logger.error("user_id={}, error={}", user_id, e)
        raise

    logger.info("user_id={}, whitelist_user={}", user_id, whitelist_user)

    return GetInvitationResponse(
        status=HTTPStatus.OK.value, whitelist_user=whitelist_user
    )


@router.post(
    "/users",
    summary="Get user data in batch",
    tags=["User"],
    response_model=GetUsersResponse,
    responses={
        200: {"model": GetUsersResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_users(
    register_request: GetUsersRequest,
):
    if not register_request.user_ids:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User ids are required",
        )

    logger.info("len(user_ids)={}", len(register_request.user_ids))

    dynamodb_service = DynamoDBService()

    try:
        user_data = dynamodb_service.batch_get_item(
            table_name=DYNAMODB_USER_TABLE,
            field_name="id",
            field_type="S",
            field_values=register_request.user_ids,
        )
        users = [to_user_model({"Item": i}) for i in user_data]
    except PrismDBException as e:
        logger.error("register_request={}, error={}", register_request, e)
        raise

    return GetUsersResponse(status=HTTPStatus.OK.value, users=users)
