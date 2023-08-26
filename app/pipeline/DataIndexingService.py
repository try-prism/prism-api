from collections.abc import Sequence

import tiktoken
from constants import (
    COHERE_API_KEY,
    DEFAULT_OPENAI_MODEL,
    PRISM_ENV,
    ZILLIZ_CLOUD_HOST,
    ZILLIZ_CLOUD_PASSWORD,
    ZILLIZ_CLOUD_PORT,
    ZILLIZ_CLOUD_USER,
)
from exceptions import PrismDBException, PrismDBExceptionCode
from llama_index import ServiceContext, StorageContext, VectorStoreIndex
from llama_index.callbacks import CallbackManager, TokenCountingHandler
from llama_index.indices.postprocessor import (
    FixedRecencyPostprocessor,
    SentenceEmbeddingOptimizer,
)
from llama_index.indices.postprocessor.cohere_rerank import CohereRerank
from llama_index.indices.query.base import BaseQueryEngine
from llama_index.llms import OpenAI
from llama_index.schema import BaseNode
from llama_index.vector_stores import MilvusVectorStore
from llama_index.vector_stores.types import NodeWithEmbedding
from loguru import logger
from pymilvus import Collection
from pymilvus.exceptions import MilvusException


class DataIndexingService:
    def __init__(self, org_id: str):
        self.org_id = org_id

        try:
            self.storage_context = StorageContext.from_defaults(
                vector_store=MilvusVectorStore(
                    # collection name can only contain numbers, letters and underscores
                    collection_name=org_id,
                    host=ZILLIZ_CLOUD_HOST,
                    port=ZILLIZ_CLOUD_PORT,
                    user=ZILLIZ_CLOUD_USER,
                    password=ZILLIZ_CLOUD_PASSWORD,
                    use_secure=True if PRISM_ENV == "PROD" else False,
                ),
            )
        except MilvusException as e:
            logger.error("org_id={}, error={}", org_id, str(e))
            raise PrismDBException(
                code=PrismDBExceptionCode.COULD_NOT_CONNECT_TO_VECTOR_STORE,
                message="Could not connect to the vector store",
            )

    def store_vectors(self, nodes: Sequence[BaseNode]) -> None:
        logger.info("org_id={}, len(nodes)={}", self.org_id, len(nodes))

        vector_index = VectorStoreIndex(
            nodes=nodes, storage_context=self.storage_context, show_progress=True
        )

        logger.info(
            "Stored index to vector store. org_id={}, index_id={}",
            self.org_id,
            vector_index.index_id,
        )

    def add_nodes(self, nodes: list[NodeWithEmbedding]) -> None:
        logger.info(
            "org_id={}, nodes={}",
            self.org_id,
            nodes,
        )

        try:
            self.storage_context.vector_store.add(nodes)
        except MilvusException as e:
            logger.error(
                "org_id={}, nodes={}, error={}",
                self.org_id,
                nodes,
                e,
            )

    def delete_nodes(self, ref_doc_ids: list[str]) -> None:
        logger.info(
            "org_id={}, ref_doc_ids={}",
            self.org_id,
            ref_doc_ids,
        )

        for ref_doc_id in ref_doc_ids:
            try:
                self.storage_context.vector_store.delete(ref_doc_id=ref_doc_id)
            except MilvusException as e:
                logger.error(
                    "org_id={}, ref_doc_id={}, error={}",
                    self.org_id,
                    ref_doc_id,
                    e,
                )

    def drop_collection(self) -> None:
        logger.info(
            "Dropping collection. org_id={}",
            self.org_id,
        )

        try:
            collection: Collection = self.storage_context.vector_store.collection
            collection.drop()
        except MilvusException as e:
            logger.error(
                "org_id={}, error={}",
                self.org_id,
                e,
            )

        logger.info(
            "Finished dropping collection. org_id={}",
            self.org_id,
        )

    def load_vector_index(self) -> VectorStoreIndex:
        logger.info("org_id={}", self.org_id)

        return VectorStoreIndex.from_vector_store(self.storage_context.vector_store)

    def generate_query_engine(self, vector_index: VectorStoreIndex) -> BaseQueryEngine:
        logger.info("org_id={}, vector_index_id={}", self.org_id, vector_index.index_id)

        token_counter = TokenCountingHandler(
            tokenizer=tiktoken.encoding_for_model(DEFAULT_OPENAI_MODEL).encode,
            verbose=True,
        )
        service_context = ServiceContext.from_defaults(
            llm=OpenAI(
                model=DEFAULT_OPENAI_MODEL,
                user=self.org_id,
                temperature=0.1,
                max_retries=3,
            ),
            chunk_size=1024,
            callback_manager=CallbackManager([token_counter]),
        )

        # prioritize most recent information in the results
        # date_key: the key in the metadata to find the date
        fixed_recency_postprocessor = FixedRecencyPostprocessor(
            tok_k=5, date_key="process_date", service_context=service_context
        )

        # re-order nodes, and returns the top N nodes
        cohere_rerank_postprocessor = CohereRerank(api_key=COHERE_API_KEY, top_n=3)

        # remove sentences that are not relevant to the query
        sentence_embedding_postprocessor = SentenceEmbeddingOptimizer(
            percentile_cutoff=0.7
        )

        query_engine = vector_index.as_query_engine(
            similarity_top_k=10,
            service_context=service_context,
            node_postprocessors=[
                cohere_rerank_postprocessor,
                fixed_recency_postprocessor,
                sentence_embedding_postprocessor,
            ],
        )

        return query_engine
