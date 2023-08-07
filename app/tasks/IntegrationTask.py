import logging

from models.RequestModels import IntegrationRequest
from pipeline import DataIndexingService, DataPipelineService
from storage import MergeService


def initiate_file_processing(
    integration_request: IntegrationRequest, account_token: str
) -> None:
    logging.info(
        "integration_request: %s, account_token=%s, Starting file processing",
        integration_request,
        account_token,
    )
    merge_service = MergeService(account_token=account_token)
    file_list = merge_service.generate_file_list()

    data_pipeline_service = DataPipelineService(account_token=account_token)
    nodes = data_pipeline_service.get_embedded_nodes(file_list)

    data_indexing_service = DataIndexingService(
        org_id=integration_request.organization_id, account_token=account_token
    )
    data_indexing_service.store_docs_to_docstore(nodes)
    data_indexing_service.store_vectors(nodes)
