import logging
import time
from http import HTTPStatus

from botocore.exceptions import ClientError
from constants import DYNAMODB_ORGANIZATION_TABLE
from exceptions import PrismDBException, PrismException, PrismMergeException
from fastapi import APIRouter, BackgroundTasks, Header
from models import get_organization_key, to_organization_model
from models.RequestModels import GenerateLinkTokenRequest, IntegrationRequest
from models.ResponseModels import (
    ErrorDTO,
    GenerateLinkTokenResponse,
    IntegrationDetailResponse,
    IntegrationRemoveResponse,
    IntegrationResponse,
)
from storage import DynamoDBService, MergeService
from tasks.IntegrationTask import initiate_file_processing

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
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid GenerateLinkTokenRequest",
        )

    logger.info(generate_request)

    merge_service = MergeService()
    try:
        link_token = merge_service.generate_link_token(
            generate_request.organization_id,
            generate_request.organization_name,
            generate_request.email_address,
        )
    except PrismMergeException as e:
        logger.error("generate_request=%s, error=%s", generate_request, e)
        return ErrorDTO(code=e.code, message=e.message)

    logger.info("generate_request=%s, link_token=%s", generate_request, link_token)
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
    background_tasks: BackgroundTasks,
):
    if (
        not integration_request.public_token
        or not integration_request.organization_id
        or not integration_request.organization_name
        or not integration_request.email_address
    ):
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value, description="Invalid IntegrationRequest"
        )

    logger.info(integration_request)

    merge_service = MergeService()
    dynamodb_service = DynamoDBService()

    try:
        # Generate Merge account_token from public_token
        account_token = merge_service.generate_account_token(
            integration_request.public_token
        )
        # Add account_token to organization's link_id_map
        response = dynamodb_service.get_organization(
            integration_request.organization_id
        )
    except PrismException as e:
        logger.error(
            "integration_request=%s, error=%s",
            integration_request,
            e,
        )
        return ErrorDTO(code=e.code, description=e.message)

    org_item = to_organization_model(response)
    timestamp = str(time.time())
    link_id_map = org_item.link_id_map
    link_id_map[account_token] = {
        "M": {
            "source": {"S": "UNKNOWN"},
            "created": {"S": timestamp},
            "status": {"S": "SYNCING"},
        }
    }

    try:
        dynamodb_service.get_client().update_item(
            TableName=DYNAMODB_ORGANIZATION_TABLE,
            Key=get_organization_key(integration_request.organization_id),
            UpdateExpression="SET link_id_map = :map, updated_at = :ua",
            ExpressionAttributeValues={
                ":map": {"M": link_id_map},
                ":ua": {"S": timestamp},
            },
        )
    except ClientError as e:
        logger.error(str(e))
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description=str(e),
        )

    # Initiate background task that processes the files to create docstore and index
    background_tasks.add_task(
        initiate_file_processing, integration_request, account_token
    )

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
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value, description="Invalid organization id"
        )

    logger.info("org_id=%s", org_id)

    # Retrieve organization's integration details
    dynamodb_service = DynamoDBService()
    try:
        response = dynamodb_service.get_organization(org_id)
    except PrismDBException as e:
        logger.error("org_id=%s, error=%s", org_id, e)
        return ErrorDTO(code=e.code, description=e.message)

    org_item = to_organization_model(response)

    try:
        link_id_map = org_item.link_id_map
        logger.info("org_id=%s, link_id_map=%s", org_id, link_id_map)
        return IntegrationDetailResponse(
            status=HTTPStatus.OK.value, integrations=link_id_map
        )

    except ClientError as e:
        logger.error(str(e))
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description=str(e),
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
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid organization id or account token",
        )

    logger.info(
        "org_id=%s, integration_account_token=%s", org_id, integration_account_token
    )

    # Remove organization's integration detail
    dynamodb_service = DynamoDBService()
    try:
        response = dynamodb_service.get_organization(org_id)
    except PrismDBException as e:
        logger.error(
            "org_id=%s, integration_account_token=%s, error=%s",
            org_id,
            integration_account_token,
            e,
        )
        return ErrorDTO(code=e.code, description=e.message)

    org_item = to_organization_model(response)
    timestamp = str(time.time())

    try:
        link_id_map = org_item.link_id_map
        logger.info("org_id=%s, link_id_map=%s", org_id, link_id_map)
        del link_id_map[integration_account_token]

        dynamodb_service.get_client().update_item(
            TableName=DYNAMODB_ORGANIZATION_TABLE,
            Key=get_organization_key(org_id),
            UpdateExpression="SET link_id_map = :map, updated_at = :ua",
            ExpressionAttributeValues={
                ":map": {"M": link_id_map},
                ":ua": {"S": timestamp},
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
