from http import HTTPStatus

from exceptions import PrismDBException, PrismException, PrismExceptionCode
from fastapi import APIRouter, Header
from loguru import logger
from models.RequestModels import (
    CancelInviteUserOrganizationRequest,
    RegisterUserRequest,
)
from models.ResponseModels import (
    DeleteUserResponse,
    ErrorDTO,
    GetInvitationResponse,
    GetUserResponse,
    RegisterUserResponse,
)
from services import CognitoService
from storage import DynamoDBService

from .organization import cancel_pending_user_invite

router = APIRouter()


"""
| Endpoint                  | Description                          | Method |
|---------------------------|--------------------------------------|--------|
| `/user`                   | Register a new user                  | POST   |
| `/user/{id}`              | Retrieve a user's details            | GET    |
| `/user/{id}`              | Update a user's details (*)          | PATCH  |
| `/user/{id}`              | Delete a user's account              | DELETE |
| `/user/{id}/invitation`   | Get invitation data from whitelist   | GET    |
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
            user_id=register_request.email,
            user_email=register_request.email,
            first_name=register_request.first_name,
            last_name=register_request.last_name,
            organization_id=whitelist_user.org_id,
        )
        # Add user to user table
        dynamodb_service.register_user(
            id=register_request.email,
            email=register_request.email,
            name=register_request.first_name + " " + register_request.last_name,
            organization_id=whitelist_user.org_id,
        )
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
        ),
    )

    return RegisterUserResponse(status=HTTPStatus.OK.value)


@router.get(
    "/user/{id}",
    summary="Retrieve a user's details",
    tags=["User"],
    response_model=GetUserResponse,
    responses={
        200: {"model": GetUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_user(id: str):
    if not id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User id is required",
        )

    logger.info("id={}", id)

    dynamodb_service = DynamoDBService()

    try:
        user = dynamodb_service.get_user(user_id=id)
    except PrismDBException as e:
        logger.error("id={}, error={}", id, e)
        raise

    return GetUserResponse(status=HTTPStatus.OK.value, user=user)


@router.delete(
    "/user/{id}",
    summary="Delete a user's account",
    tags=["User"],
    response_model=DeleteUserResponse,
    responses={
        200: {"model": DeleteUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def delete_user(id: str, org_admin_id: str = Header()):
    if not id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User id is required",
        )

    logger.info("id={}", id)

    dynamodb_service = DynamoDBService()
    cognito_service = CognitoService()

    try:
        dynamodb_service.remove_user(user_id=id, org_admin_id=org_admin_id)
        cognito_service.remove_user(user_id=id)
    except PrismException as e:
        logger.error("id={}, org_admin_id={}, error={}", id, org_admin_id, e)
        raise

    return DeleteUserResponse(status=HTTPStatus.OK.value)


@router.get(
    "/user/{id}/invitation",
    summary="Get invitation data from whitelist",
    tags=["User"],
    response_model=GetInvitationResponse,
    responses={
        200: {"model": GetInvitationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_invitation_data(id: str):
    if not id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="User id is required",
        )

    logger.info("id={}", id)

    dynamodb_service = DynamoDBService()

    try:
        whitelist_user = dynamodb_service.get_whitelist_user_data(user_id=id)
    except PrismDBException as e:
        logger.error("id={}, error={}", id, e)
        raise

    logger.info("id={}, whitelist_user={}", id, whitelist_user)

    return GetInvitationResponse(
        status=HTTPStatus.OK.value, whitelist_user=whitelist_user
    )
