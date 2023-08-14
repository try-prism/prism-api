import time

from enums import IntegrationStatus
from loguru import logger
from models.RequestModels import IntegrationRequest
from pipeline import DataIndexingService, DataPipelineService
from storage import DynamoDBService, MergeService


def initiate_file_processing(
    integration_request: IntegrationRequest, account_token: str
) -> None:
    logger.info(
        "integration_request: {}, account_token={}, Starting file processing",
        integration_request,
        account_token,
    )

    dynamodb_service = DynamoDBService()
    merge_service = MergeService(account_token=account_token)

    try:
        logger.info(
            "Checking for merge sync status. integration_request={}",
            integration_request,
        )
        status = merge_service.check_sync_status()

        # Wait for the Merge sync to complete before continuing
        while not status:
            time.sleep(120)  # 120 seconds
            status = merge_service.check_sync_status()

        logger.info("Generating file list. integration_request={}", integration_request)
        file_list = merge_service.generate_file_list()

        logger.info(
            "Modifying integration status to INDEXING. integration_request={}",
            integration_request,
        )
        dynamodb_service.modify_integration_status(
            org_id=integration_request.organization_id,
            account_token=account_token,
            status=IntegrationStatus.INDEXING,
        )

        logger.info(
            "Creating data pipeline service. integration_request={}",
            integration_request,
        )
        data_pipeline_service = DataPipelineService(
            org_id=integration_request.organization_id, account_token=account_token
        )
        logger.info(
            "Generating embedded node vectors. integration_request={}",
            integration_request,
        )
        nodes = data_pipeline_service.get_embedded_nodes(file_list)

        data_indexing_service = DataIndexingService(
            org_id=integration_request.organization_id
        )
        logger.info(
            "Storing embedded node vectors. integration_request={}", integration_request
        )
        data_indexing_service.store_vectors(nodes)
    except Exception as e:
        logger.error(
            "integration_request: {}, account_token={}, error={}",
            integration_request,
            account_token,
            e,
        )
        dynamodb_service.modify_integration_status(
            org_id=integration_request.organization_id,
            account_token=account_token,
            status=IntegrationStatus.FAIL,
        )
        return

    dynamodb_service.modify_integration_status(
        org_id=integration_request.organization_id,
        account_token=account_token,
        status=IntegrationStatus.SUCCESS,
    )
