import json

from connection import ConnectionManager
from constants import DYNAMODB_FILE_TABLE
from exceptions import PrismDBException, PrismDBExceptionCode
from fastapi import APIRouter, Header, WebSocket, WebSocketDisconnect
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
async def query(websocket: WebSocket, org_id: str = Header(), user_id: str = Header()):
    logger.info("org_id: %s, user_id: %s, Session Started", org_id, user_id)

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
        logger.error("org_id=%s, user_id: %s, error=%s", org_id, user_id, e)
        return

    manager = ConnectionManager()
    await manager.connect(websocket)

    try:
        while True:
            user_text = await websocket.receive_text()
            response = await chat_engine.achat(message=user_text)
            await manager.send_message(response.response, websocket)

            try:
                source_node_ids = set(
                    [
                        i.node.relationships[NodeRelationship.SOURCE].node_id
                        for i in response.source_nodes
                    ]
                )

                batch_data = dynamodb_service.batch_get_item(
                    table_name=DYNAMODB_FILE_TABLE,
                    field_name="id",
                    field_type="S",
                    field_values=list(source_node_ids),
                )
                files = [to_file_model({"Item": i}) for i in batch_data]
                file_mapping = [{"name": i.name, "url": i.file_url} for i in files]

                await manager.send_message(
                    f"**SOURCE**{json.dumps(file_mapping)}", websocket
                )
            except Exception as e:
                logger.error(
                    "user_text=%s, response=%s, error=%s", user_text, response, e
                )
                await manager.send_message("**FAIL**", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

    logger.info("org_id: %s, user_id: %s, Session Ended", org_id, user_id)
