from http import HTTPStatus

from exceptions import (
    PrismDBException,
    PrismException,
    PrismExceptionCode,
    PrismMergeException,
)
from fastapi import APIRouter, BackgroundTasks, Header
from loguru import logger
from models.RequestModels import IntegrationRemoveRequest, IntegrationRequest
from models.ResponseModels import (
    ErrorDTO,
    GenerateLinkTokenResponse,
    IntegrationDetailResponse,
    IntegrationRemoveResponse,
    IntegrationResponse,
)
from pipeline import DataIndexingService
from storage import DynamoDBService, MergeService
from tasks.IntegrationTask import initiate_file_processing

router = APIRouter()

"""
| Endpoint                           | Description                          | Method |
|------------------------------------|--------------------------------------|--------|
| `/integration`                     | Add a new cloud storage integration  | POST   |
| `/integration/{org_id}`            | Retrieve integration details         | GET    |
| `/integration/{org_id}`            | Remove a cloud storage integration   | DELETE |
| `/integration/{org_id}/generate`   | Generate link token for integration  | GET    |
"""


@router.post(
    "/integration",
    summary="Add a new cloud storage integration",
    tags=["Integration"],
    response_model=IntegrationResponse,
    responses={
        200: {"model": IntegrationResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
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
        or not integration_request.organization_admin_id
    ):
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST, message="Invalid IntegrationRequest"
        )

    logger.info("integration_request={}", integration_request)

    merge_service = MergeService()
    dynamodb_service = DynamoDBService()

    try:
        # Generate Merge account_token from public_token
        account_token = merge_service.generate_account_token(
            integration_request.public_token
        )
        # Add account_token to organization's link_id_map
        integration_item = dynamodb_service.add_integration(
            org_id=integration_request.organization_id,
            org_admin_id=integration_request.organization_admin_id,
            account_token=account_token,
        )
    except PrismException as e:
        logger.error(
            "integration_request={}, error={}",
            integration_request,
            e,
        )
        raise

    # Initiate background task that processes the files to create docstore and index
    background_tasks.add_task(
        initiate_file_processing, integration_request, account_token
    )

    return IntegrationResponse(
        status=HTTPStatus.OK.value, integration_item=integration_item
    )


@router.get(
    "/integration/{org_id}",
    summary="Retrieve integration details",
    tags=["Integration"],
    response_model=IntegrationDetailResponse,
    responses={
        200: {"model": IntegrationDetailResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def get_integration_detail(
    org_id: str,
):
    if not org_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST, message="Invalid organization id"
        )

    logger.info("org_id={}", org_id)

    # Retrieve organization's integration details
    dynamodb_service = DynamoDBService()

    try:
        organization = dynamodb_service.get_organization(org_id)
        link_id_map = organization.link_id_map
        logger.info("org_id={}, link_id_map={}", org_id, link_id_map)

        return IntegrationDetailResponse(
            status=HTTPStatus.OK.value, integrations=link_id_map
        )
    except PrismDBException as e:
        logger.error("org_id={}, error={}", org_id, e)
        raise


@router.delete(
    "/integration/{org_id}",
    summary="Remove a cloud storage integration",
    tags=["Integration"],
    response_model=IntegrationRemoveResponse,
    responses={
        200: {"model": IntegrationRemoveResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def remove_integration_detail(
    org_id: str,
    remove_request: IntegrationRemoveRequest,
    integration_account_token: str = Header(),
):
    if (
        not org_id
        or not integration_account_token
        or not remove_request.organization_admin_id
    ):
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid organization id or account token or admin id",
        )

    logger.info(
        "org_id={}, integration_account_token={}, remove_request={}",
        org_id,
        integration_account_token,
        remove_request,
    )

    dynamodb_service = DynamoDBService()
    data_index_service = DataIndexingService(org_id=org_id)
    merge_service = MergeService(account_token=integration_account_token)

    try:
        organization = dynamodb_service.get_organization(org_id=org_id)

        # Check if the user is an admin of the organization
        if organization.admin_id != remove_request.organization_admin_id:
            logger.error(
                "org_id={}, integration_account_token={}, remove_request={}, error={}",
                org_id,
                integration_account_token,
                remove_request,
                "You don't have permission",
            )
            raise PrismException(
                code=PrismExceptionCode.BAD_REQUEST, message="You don't have permission"
            )

        # Remove data related to this integration from file database
        related_file_ids = dynamodb_service.get_all_file_ids_for_integration(
            account_token=integration_account_token
        )
        dynamodb_service.modify_file_in_batch(file_ids=related_file_ids, is_remove=True)

        # Remove data related to this integration from vector store
        data_index_service.delete_nodes(related_file_ids)

        # Remove data related to this integration from organization database
        dynamodb_service.modify_organization_files(
            org_id=org_id, file_ids=related_file_ids, is_remove=True
        )

        # Remove organization's integration detail
        dynamodb_service.remove_integration(
            org_id=org_id, account_token=integration_account_token
        )

        # Remove link from Merge
        merge_service.remove_integration()
    except PrismException as e:
        logger.error(
            "org_id={}, integration_account_token={}, remove_request={}, error={}",
            org_id,
            integration_account_token,
            remove_request,
            e,
        )
        raise

    return IntegrationRemoveResponse(status=HTTPStatus.OK.value)


@router.get(
    "/integration/{org_id}/generate",
    summary="Generate link token for integration",
    tags=["Integration"],
    response_model=GenerateLinkTokenResponse,
    responses={
        200: {"model": GenerateLinkTokenResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def generate_link_token(org_id: str):
    if not org_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid GenerateLinkTokenRequest",
        )

    logger.info("org_id={}", org_id)

    dynamodb_service = DynamoDBService()
    merge_service = MergeService()

    try:
        organization = dynamodb_service.get_organization(org_id)
        link_token = merge_service.generate_link_token(
            org_id,
            organization.name,
            organization.email,
        )
    except PrismMergeException as e:
        logger.error("org_id={}, error={}", org_id, e)
        raise

    logger.info(
        "org_id={}, link_token={}",
        org_id,
        link_token,
    )
    return GenerateLinkTokenResponse(status=HTTPStatus.OK.value, link_token=link_token)
