import logging

from connection import ConnectionManager
from exceptions import PrismDBException, PrismDBExceptionCode
from fastapi import APIRouter, Header, WebSocket, WebSocketDisconnect
from models import to_organization_model
from pipeline import DataIndexingService
from storage import DynamoDBService

router = APIRouter()
logger = logging.getLogger(__name__)

"""
| Endpoint                  | Description                              | Method |
|---------------------------|------------------------------------------|--------|
| `/query`                  | Perform a search query on files          | SOCKET |
"""


@router.websocket("/query")
async def query(websocket: WebSocket, org_id: str = Header(), user_id: str = Header()):
    logger.info("org_id: %s, user_id: %s, Session Started", org_id, user_id)

    dynamodb_service = DynamoDBService()

    try:
        # Check whether the user belongs to the organization
        response = dynamodb_service.get_organization(org_id)
        org_model = to_organization_model(response)

        if user_id not in org_model.user_list:
            raise PrismDBException(
                code=PrismDBExceptionCode.USER_DOES_NOT_EXIST,
                message="User doesn't belong to this organization",
            )

        # Create chat index that queries the given organization
        data_index_service = DataIndexingService(org_id=org_id)

        vector_index = data_index_service.load_vector_index()
        chat_engine = data_index_service.generate_chat_engine(vector_index)

    except PrismDBException as e:
        logger.error("org_id=%s, user_id: %s, error=%s", org_id, user_id, e)
        return

    manager = ConnectionManager()
    await manager.connect(websocket)

    try:
        while True:
            user_text = await websocket.receive_text()
            response = await chat_engine.achat(message=user_text)
            await manager.send_message(response.response, websocket)
            logger.debug("source_nodes=%s", response.source_nodes)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{user_id} left the chat")

    logger.info("org_id: %s, user_id: %s, Session Ended", org_id, user_id)
