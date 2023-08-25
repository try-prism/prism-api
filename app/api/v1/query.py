import json

from connection import ConnectionManager
from constants import DYNAMODB_FILE_TABLE
from exceptions import (
    PrismDBException,
    PrismDBExceptionCode,
    PrismException,
    PrismExceptionCode,
)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from llama_index.schema import NodeRelationship
from loguru import logger
from models import to_file_model
from pipeline import DataIndexingService
from storage import DynamoDBService

router = APIRouter()


"""
| Endpoint                  | Description                              | Method |
|---------------------------|------------------------------------------|--------|
| `/query`                  | Perform a search query on files          | SOCKET |
"""


@router.websocket("/query")
async def query(
    websocket: WebSocket,
    org_id: str = "",
    user_id: str = "",
):
    if not org_id or not user_id:
        raise PrismException(
            code=PrismExceptionCode.BAD_REQUEST,
            message="Invalid Credentials",
        )

    logger.info("org_id={}, user_id={}, Session Started", org_id, user_id)

    dynamodb_service = DynamoDBService()

    try:
        # Check whether the user belongs to the organization
        organization = dynamodb_service.get_organization(org_id)

        if user_id not in organization.user_list:
            raise PrismDBException(
                code=PrismDBExceptionCode.USER_DOES_NOT_EXIST,
                message="User doesn't belong to this organization",
            )

        # Create chat index that queries the given organization
        data_index_service = DataIndexingService(org_id=org_id)

        vector_index = data_index_service.load_vector_index()
        chat_engine = data_index_service.generate_chat_engine(vector_index)

    except PrismDBException as e:
        logger.error("org_id={}, user_id: {}, error={}", org_id, user_id, e)
        return

    manager = ConnectionManager()
    await manager.connect(websocket)

    try:
        while True:
            user_text = await websocket.receive_text()
            payload = {}

            try:
                response = await chat_engine.achat(message=user_text)
                logger.info("response={}", response)
                payload["response"] = response.response
            except Exception as e:
                logger.error("user_text={}, error={}", user_text, e)
                payload["response"] = "Please try again later"

            try:
                logger.info("source_nodes={}", response.source_nodes)
                source_node_ids = set(
                    [
                        i.node.relationships[NodeRelationship.SOURCE].node_id
                        for i in response.source_nodes
                    ]
                )
                logger.info("source_node_ids={}", source_node_ids)

                batch_data = dynamodb_service.batch_get_item(
                    table_name=DYNAMODB_FILE_TABLE,
                    field_name="id",
                    field_type="S",
                    field_values=list(source_node_ids),
                )
                files = [to_file_model({"Item": i}) for i in batch_data]
                file_mapping = [{"name": i.name, "url": i.file_url} for i in files]
                payload["sources"] = file_mapping
            except Exception as e:
                logger.error(
                    "user_text={}, response={}, error={}", user_text, response, e
                )

            await manager.send_message(json.dumps(payload), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

    logger.info("org_id: {}, user_id: {}, Session Ended", org_id, user_id)
