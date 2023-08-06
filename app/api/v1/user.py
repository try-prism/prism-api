import logging
from http import HTTPStatus

from fastapi import APIRouter, Header
from models import to_whitelist_model
from models.RequestModels import (
    CancelInviteUserOrganizationRequest,
    RegisterUserRequest,
)
from models.ResponseModels import (
    CancelInviteUserOrganizationResponse,
    DeleteUserResponse,
    ErrorDTO,
    GetInvitationResponse,
    GetUserResponse,
    RegisterUserResponse,
)
from models.UserModel import to_user_model
from storage import DynamoDBService

from .organization import cancel_pending_user_invite

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint             | Description                          | Method |
|----------------------|--------------------------------------|--------|
| `/user`              | Register a new user                  | POST   |
| `/user/{id}`         | Retrieve a user's details            | GET    |
| `/user/{id}`         | Update a user's details (*)          | PATCH  |
| `/user/{id}`         | Delete a user's account              | DELETE |
| `/invitation/{id}`   | Get invitation data from whitelist   | GET    |
"""


@router.post(
    "/user",
    summary="Register a new user",
    tags=["User"],
    response_model=RegisterUserResponse,
    responses={
        200: {"model": RegisterUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def register_user(
    register_request: RegisterUserRequest,
):
    if (
        not register_request.id
        or not register_request.email
        or not register_request.name
    ):
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid RegisterUserRequest",
        )

    logger.info("register_request=%s", register_request)

    dynamodb_service = DynamoDBService()
    whitelist_response = dynamodb_service.get_whitelist_user_data(
        user_id=register_request.id
    )

    if not whitelist_response:
        logger.error(
            "register_request=%s, error=User is not listed in whitelist",
            register_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="User is not invited to join",
        )

    whitelist_item = to_whitelist_model(whitelist_response)
    logger.info(
        "register_request=%s, whitelist_item=%s", register_request, whitelist_item
    )

    register_response = dynamodb_service.register_user(
        id=register_request.id,
        email=register_request.email,
        name=register_request.name,
        organization_id=whitelist_item.org_id,
    )

    if not register_response:
        logger.error(
            "register_request=%s, error=Failed to register user",
            register_request,
        )
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Failed to register user",
        )

    remove_request = cancel_pending_user_invite(
        org_id=whitelist_item.org_id,
        cancel_request=CancelInviteUserOrganizationRequest(
            organization_name=whitelist_item.org_name,
            organization_user_id=whitelist_item.id,
        ),
    )

    if type(remove_request) is not CancelInviteUserOrganizationResponse:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Failed to remove user id from whitelist after registration",
        )

    return RegisterUserResponse(status=HTTPStatus.OK.value)


@router.get(
    "/user/{id}",
    summary="Retrieve a user's details",
    tags=["User"],
    response_model=GetUserResponse,
    responses={
        200: {"model": GetUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def get_user(id: str):
    if not id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="User id is required",
        )

    logger.info("id=%s", id)

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_user(user_id=id)

    if not response:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="No such user",
        )

    return GetUserResponse(status=HTTPStatus.OK.value, user=to_user_model(response))


@router.delete(
    "/user/{id}",
    summary="Delete a user's account",
    tags=["User"],
    response_model=DeleteUserResponse,
    responses={
        200: {"model": DeleteUserResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def delete_user(id: str, org_admin_id: str = Header()):
    if not id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="User id is required",
        )

    logger.info("id=%s", id)

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_user(user_id=id)

    if not response:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="No such user",
        )

    remove_response = dynamodb_service.remove_user(
        user_id=id, org_admin_id=org_admin_id
    )

    if not remove_response:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Failed to remove user",
        )

    # TODO: remove the user from the cognito

    return DeleteUserResponse(status=HTTPStatus.OK.value)


@router.get(
    "/invitation/{id}",
    summary="Get invitation data from whitelist",
    tags=["User"],
    response_model=GetInvitationResponse,
    responses={
        200: {"model": GetInvitationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def get_invitation_data(id: str):
    if not id:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="User id is required",
        )

    logger.info("id=%s", id)

    dynamodb_service = DynamoDBService()
    response = dynamodb_service.get_whitelist_user_data(user_id=id)

    if not response:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="User is not invited to join",
        )

    whitelist_item = to_whitelist_model(response)
    logger.info("id=%s, whitelist_item=%s", id, whitelist_item)

    return GetInvitationResponse(status=HTTPStatus.OK.value, invitation=whitelist_item)
