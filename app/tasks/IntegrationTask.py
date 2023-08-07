import logging

from models.RequestModels import IntegrationRequest
from pipeline import DataIndexingService, DataPipelineService
from storage import DynamoDBService, MergeService


def initiate_file_processing(
    integration_request: IntegrationRequest, account_token: str
) -> None:
    logging.info(
        "integration_request: %s, account_token=%s, Starting file processing",
        integration_request,
        account_token,
    )

    dynamodb_service = DynamoDBService()

    try:
        merge_service = MergeService(account_token=account_token)
        file_list = merge_service.generate_file_list()

        dynamodb_service.add_integration(
            org_id=integration_request.organization_id,
            account_token=account_token,
            status="INDEXING",
        )

        data_pipeline_service = DataPipelineService(account_token=account_token)
        nodes = data_pipeline_service.get_embedded_nodes(file_list)

        data_indexing_service = DataIndexingService(
            org_id=integration_request.organization_id, account_token=account_token
        )
        data_indexing_service.store_docs_to_docstore(nodes)
        data_indexing_service.store_vectors(nodes)
    except Exception as e:
        logging.error(
            "integration_request: %s, account_token=%s, error=%s",
            integration_request,
            account_token,
            str(e),
        )
        dynamodb_service.add_integration(
            org_id=integration_request.organization_id,
            account_token=account_token,
            status="FAILED",
        )
        return

    dynamodb_service.add_integration(
        org_id=integration_request.organization_id,
        account_token=account_token,
        status="SUCCESS",
    )