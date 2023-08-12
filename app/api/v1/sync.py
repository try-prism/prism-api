import logging
from http import HTTPStatus

from constants import DYNAMODB_FILE_TABLE
from enums import FileOperation
from exceptions import PrismAPIException, PrismException
from fastapi import APIRouter
from merge.resources.filestorage.types import File
from models import to_file_model
from models.RequestModels import SyncOrganizationDataRequest
from models.ResponseModels import ErrorDTO, SyncOrganizationDataResponse
from pipeline import DataIndexingService, DataPipelineService
from storage import DynamoDBService
from utils import divide_list

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint              | Description                                            | Method |
|-----------------------|--------------------------------------------------------|--------|
| `/sync/{org_id}`      | Sync organization's vector store with current data     | PATCH  |
"""


@router.patch(
    "/sync/{org_id}",
    summary="Sync organization's vector store with current data",
    tags=["Sync"],
    response_model=SyncOrganizationDataResponse,
    responses={
        200: {"model": SyncOrganizationDataResponse, "description": "OK"},
        400: {"model": ErrorDTO, "message": "Error: Bad request"},
    },
)
async def sync_organization_data(
    org_id: str,
    sync_request: SyncOrganizationDataRequest,
):
    if not sync_request.account_token or not sync_request.files:
        raise PrismAPIException(
            code=HTTPStatus.BAD_REQUEST.value,
            message="Invalid SyncOrganizationDataRequest",
        )

    logger.info("sync_request=%s, org_id=%s", sync_request, org_id)

    dynamodb_service = DynamoDBService()
    data_index_service = DataIndexingService(org_id=org_id)
    data_pipeline_service = DataPipelineService(
        org_id=org_id, account_token=sync_request.account_token
    )

    id_batches = {
        FileOperation.CREATED: [],
        FileOperation.UPDATED: [],
        FileOperation.DELETED: [],
    }

    for file in sync_request.files:
        id_batches[file.operation].append(file.id)

    files: list[File] = []
    file_id_batch: list[str] = divide_list(
        id_batches[FileOperation.CREATED] + id_batches[FileOperation.UPDATED], 50
    )

    try:
        # Remove old data nodes
        remove_ids = (
            id_batches[FileOperation.UPDATED] + id_batches[FileOperation.DELETED]
        )
        data_index_service.delete_nodes(remove_ids)

        # Remove file data from file table and organization
        dynamodb_service.modify_organization_files(
            org_id=org_id, file_ids=remove_ids, is_remove=True
        )
        dynamodb_service.modify_file_in_batch(file_ids=remove_ids, is_remove=True)

        # Get files
        for batch in file_id_batch:
            batch_data = dynamodb_service.batch_get_item(
                DYNAMODB_FILE_TABLE, "id", batch
            )
            files.extend([to_file_model(i) for i in batch_data])

        # Generate & add new data nodes
        nodes = data_pipeline_service.get_embedded_nodes(all_files=files)
        data_index_service.add_nodes(nodes)
    except PrismException as e:
        logger.error("sync_request=%s, error=%s", sync_request, e)
        raise PrismAPIException(
            code=e.code.value,
            message=e.message,
        )

    return SyncOrganizationDataResponse(status=HTTPStatus.OK.value)
