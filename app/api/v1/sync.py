import logging
from http import HTTPStatus

from exceptions import PrismDBException
from fastapi import APIRouter
from models.RequestModels import SyncOrganizationDataRequest
from models.ResponseModels import ErrorDTO, SyncOrganizationDataResponse

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
        400: {"model": ErrorDTO, "description": "Error: Bad request"},
    },
)
async def register_organization(
    org_id: str,
    sync_request: SyncOrganizationDataRequest,
):
    if not sync_request.file_ids:
        return ErrorDTO(
            code=HTTPStatus.BAD_REQUEST.value,
            description="Invalid RegisterOrganizationRequest",
        )

    logger.info("sync_request=%s, org_id=%s", sync_request, org_id)

    try:
        # TODO: Implement deleting from vector store and adding to vector store
        pass
    except PrismDBException as e:
        logger.error("sync_request=%s, error=%s", sync_request, e)
        return ErrorDTO(
            code=e.code,
            description=e.message,
        )

    return SyncOrganizationDataResponse(status=HTTPStatus.OK.value)
