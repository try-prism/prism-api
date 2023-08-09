import logging
import time
from collections.abc import Sequence

import tiktoken
from botocore.exceptions import ClientError
from constants import (
    COHERE_API_KEY,
    DEFAULT_OPENAI_MODEL,
    DYNAMODB_ORGANIZATION_TABLE,
    ZILLIZ_CLOUD_HOST,
    ZILLIZ_CLOUD_PASSWORD,
    ZILLIZ_CLOUD_PORT,
    ZILLIZ_CLOUD_USER,
)
from exceptions import PrismDBException, PrismDBExceptionCode
from llama_index import (
    ServiceContext,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.callbacks import CallbackManager, TokenCountingHandler
from llama_index.chat_engine.types import BaseChatEngine, ChatMode
from llama_index.indices.postprocessor import (
    FixedRecencyPostprocessor,
    SentenceEmbeddingOptimizer,
)
from llama_index.indices.postprocessor.cohere_rerank import CohereRerank
from llama_index.llms import OpenAI
from llama_index.schema import BaseNode
from llama_index.vector_stores import MilvusVectorStore
from models import get_organization_key, to_organization_model
from storage import DynamoDBService

logger = logging.getLogger(__name__)


class DataIndexingService:
    def __init__(self, org_id: str, account_token: str | None = ""):
        self.org_id = org_id
        self.account_token = account_token
        self.storage_context = StorageContext.from_defaults(
            vector_store=MilvusVectorStore(
                collection_name=org_id,
                host=ZILLIZ_CLOUD_HOST,
                port=ZILLIZ_CLOUD_PORT,
                user=ZILLIZ_CLOUD_USER,
                password=ZILLIZ_CLOUD_PASSWORD,
                use_secure=True,
            ),
        )

    def store_vectors(self, nodes: Sequence[BaseNode]) -> None:
        logger.info(
            "Storing vectors & index. org_id=%s, account_token=%s",
            self.org_id,
            self.account_token,
        )

        ray_docs_index = VectorStoreIndex(
            nodes=nodes, storage_context=self.storage_context
        )

        # Store vector index id to organization
        dynamodb_service = DynamoDBService()

        try:
            dynamodb_service.get_organization(self.org_id)
        except PrismDBException as e:
            logger.error(
                "org_id=%s, account_token=%s, error=%s",
                self.org_id,
                self.account_token,
                e,
            )
            raise e

        timestamp = str(time.time())

        try:
            dynamodb_service.get_client().update_item(
                TableName=DYNAMODB_ORGANIZATION_TABLE,
                Key=get_organization_key(self.org_id),
                UpdateExpression="SET index_id = :id, updated_at = :ua",
                ExpressionAttributeValues={
                    ":id": {"S": ray_docs_index.index_id},
                    ":ua": {"S": timestamp},
                },
            )
        except ClientError as e:
            logger.error(
                "org_id=%s, account_token=%s, error=%s",
                self.org_id,
                self.account_token,
                str(e),
            )
            raise PrismDBException(
                code=PrismDBExceptionCode.ITEM_UPDATE_ERROR,
                message="Failed to append index id to organization",
            )

    def load_vector_index(self) -> VectorStoreIndex:
        logger.info(
            "Loading vector index. org_id=%s",
            self.org_id,
        )

        dynamodb_service = DynamoDBService()

        response = dynamodb_service.get_organization(self.org_id)
        org_item = to_organization_model(response)
        vector_index_id = org_item.index_id

        vector_index = load_index_from_storage(
            storage_context=self.storage_context, index_id=vector_index_id
        )

        return vector_index

    def generate_chat_engine(self, vector_index: VectorStoreIndex) -> BaseChatEngine:
        token_counter = TokenCountingHandler(
            tokenizer=tiktoken.encoding_for_model(DEFAULT_OPENAI_MODEL).encode,
            verbose=True,
        )
        service_context = ServiceContext.from_defaults(
            llm=OpenAI(
                model=DEFAULT_OPENAI_MODEL,
                user=self.org_id,
                temperature=0,
                max_retries=3,
            ),
            chunk_size=1024,
            callback_manager=CallbackManager([token_counter]),
        )

        # prioritize most recent information in the results
        fixed_recency_postprocessor = FixedRecencyPostprocessor(
            tok_k=5, date_key="process_date"  # the key in the metadata to find the date
        )

        # re-order nodes, and returns the top N nodes
        cohere_rerank_postprocessor = CohereRerank(
            api_key=COHERE_API_KEY, top_n=self.top_k
        )
        # remove sentences that are not relevant to the query
        sentence_embedding_postprocessor = SentenceEmbeddingOptimizer(
            percentile_cutoff=0.7
        )

        chat_engine = vector_index.as_chat_engine(
            similarity_top_k=self.top_k,
            service_context=service_context,
            chat_mode=ChatMode.REACT,
            node_postprocessors=[
                cohere_rerank_postprocessor,
                fixed_recency_postprocessor,
                sentence_embedding_postprocessor,
            ],
        )

        return chat_engine
