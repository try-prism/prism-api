import logging
import time
from http import HTTPStatus

import requests
from botocore.exceptions import ClientError
from constants import DYNAMODB_ORGANIZATION_TABLE, MERGE_API_KEY
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from models.RequestModels import GenerateLinkTokenRequest, IntegrationRequest
from models.ResponseModels import (
    ErrorDTO,
    GenerateLinkTokenResponse,
    IntegrationDetailResponse,
    IntegrationRemoveResponse,
    IntegrationResponse,
)
from storage import DynamoDBService

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint                      | Description                          | Method |
|-------------------------------|--------------------------------------|--------|
| `/integration`                | Add a new cloud storage integration  | POST   |
| `/integration/{org_id}`       | Retrieve integration details         | GET    |
| `/integration/{org_id}`       | Remove a cloud storage integration   | DELETE |
| `/generate-link-token`        | Generate link token for integration  | POST   |
"""


@router.post(
    "/generate-link-token",
    summary="Generate link token for integration",
    tags=["Integration"],
    response_model=GenerateLinkTokenResponse,
    responses={
        200: {"model": GenerateLinkTokenResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def generate_link_token(
    generate_request: GenerateLinkTokenRequest,
):
    if (
        not generate_request.organization_id
        or not generate_request.organization_name
        or not generate_request.email_address
    ):
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "Invalid GenerateLinkTokenRequest",
            },
        )

    logger.info(generate_request)

    headers = {"Authorization": f"Bearer {MERGE_API_KEY}"}
    body = {
        "end_user_origin_id": generate_request.organization_id,  # unique entity ID
        "end_user_organization_name": generate_request.organization_name,  # organization name
        "end_user_email_address": generate_request.email_address,  # email address
        "categories": ["filestorage"],
    }

    link_token_url = "https://api.merge.dev/api/integrations/create-link-token"
    link_token_result = requests.post(link_token_url, data=body, headers=headers)
    link_token = link_token_result.json().get("link_token")
    logger.info(f"generate_request={generate_request}, link_token={link_token}")

    return GenerateLinkTokenResponse(status=HTTPStatus.OK.value, link_token=link_token)


@router.post(
    "/integration",
    summary="Add a new cloud storage integration",
    tags=["Integration"],
    response_model=IntegrationResponse,
    responses={
        200: {"model": IntegrationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def integration(
    integration_request: IntegrationRequest,
):
    if (
        not integration_request.public_token
        or not integration_request.organization_id
        or not integration_request.organization_name
        or not integration_request.email_address
    ):
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "Invalid IntegrationRequest",
            },
        )

    logger.info(integration_request)

    # Generate Merge account_token from public_token
    headers = {"Authorization": f"Bearer {MERGE_API_KEY}"}
    account_token_url = f"https://api.merge.dev/api/integrations/account-token/{integration_request.public_token}"
    account_token_result = requests.get(account_token_url, headers=headers)
    account_token = account_token_result.json().get("account_token")

    # Add account_token to organization's link_id_map
    dynamodb_service = DynamoDBService()

    key = {"id": {"S": integration_request.organization_id}}
    response = dynamodb_service.get_item(DYNAMODB_ORGANIZATION_TABLE, key)

    if not response:
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "No such organization exists",
            },
        )

    org_item = response["Item"]
    timestamp = str(time.time())

    try:
        link_id_map: dict = org_item.get("link_id_map", {"M": {}})["M"]
        link_id_map[account_token] = {
            "M": {"source": {"S": "UNKNOWN"}, "created": {"S": timestamp}}
        }

        dynamodb_service.get_client().update_item(
            TableName=DYNAMODB_ORGANIZATION_TABLE,
            Key=key,
            UpdateExpression="SET link_id_map = :map, updated_at = :ua",
            ExpressionAttributeValues={
                ":map": {"M": link_id_map},
                ":ua": {"S": timestamp},
            },
        )
    except ClientError as e:
        logger.error(str(e))
        return IntegrationResponse(status=HTTPStatus.FORBIDDEN.value)

    # TODO: process file processing here

    return IntegrationResponse(status=HTTPStatus.OK.value)


@router.get(
    "/integration/{org_id}",
    summary="Retrieve integration details",
    tags=["Integration"],
    response_model=IntegrationDetailResponse,
    responses={
        200: {"model": IntegrationDetailResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def get_integration_detail(
    org_id: str,
):
    if not org_id:
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "Invalid organization id",
            },
        )

    logger.info(f"org_id={org_id}")

    # Retrieve organization's integration details
    dynamodb_service = DynamoDBService()

    key = {"id": {"S": org_id}}
    response = dynamodb_service.get_item(DYNAMODB_ORGANIZATION_TABLE, key)

    if not response:
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "No such organization exists",
            },
        )

    org_item = response["Item"]

    try:
        link_id_map = org_item.get("link_id_map", {"M": {}})["M"]
        logger.info(f"link_id_map={link_id_map}")
        return IntegrationDetailResponse(
            status=HTTPStatus.OK.value, integrations=link_id_map
        )

    except ClientError as e:
        logger.error(str(e))
        return IntegrationDetailResponse(
            status=HTTPStatus.FORBIDDEN.value, integrations=[]
        )


@router.delete(
    "/integration/{org_id}",
    summary="Remove a cloud storage integration",
    tags=["Integration"],
    response_model=IntegrationRemoveResponse,
    responses={
        200: {"model": IntegrationRemoveResponse, "description": "OK"},
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def remove_integration_detail(
    org_id: str,
    integration_account_token: str = Header(),
):
    if not org_id or not integration_account_token:
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "Invalid organization id or account token",
            },
        )

    logger.info(
        f"org_id={org_id}, integration_account_token={integration_account_token}"
    )

    # Remove organization's integration detail
    dynamodb_service = DynamoDBService()

    key = {"id": {"S": org_id}}
    response = dynamodb_service.get_item(DYNAMODB_ORGANIZATION_TABLE, key)

    if not response:
        return JSONResponse(
            status_code=400,
            content={
                "code": HTTPStatus.BAD_REQUEST,
                "description": "No such organization exists",
            },
        )

    org_item = response["Item"]
    timestamp = str(time.time())

    try:
        link_id_map = org_item.get("link_id_map", {"M": {}})["M"]
        logger.info(f"link_id_map={link_id_map}")
        del link_id_map[integration_account_token]

        dynamodb_service.get_client().update_item(
            TableName=DYNAMODB_ORGANIZATION_TABLE,
            Key=key,
            UpdateExpression="SET link_id_map = :map, last_updated = :lu",
            ExpressionAttributeValues={
                ":map": {"M": link_id_map},
                ":lu": {"S": timestamp},
            },
        )
    except ClientError as e:
        logger.error(str(e))
        return ErrorDTO(code=HTTPStatus.FORBIDDEN.value, description=str(e))
    except Exception as e:
        logger.error(str(e))
        return ErrorDTO(code=HTTPStatus.FORBIDDEN.value, description=str(e))

    # TODO: Remove data related to this integration

    return IntegrationRemoveResponse(status=HTTPStatus.OK.value)
