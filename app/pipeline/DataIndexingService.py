import logging
from collections.abc import Sequence

import tiktoken
from constants import (
    COHERE_API_KEY,
    DEFAULT_OPENAI_MODEL,
    ZILLIZ_CLOUD_HOST,
    ZILLIZ_CLOUD_PASSWORD,
    ZILLIZ_CLOUD_PORT,
    ZILLIZ_CLOUD_USER,
)
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
from llama_index.vector_stores.types import NodeWithEmbedding
from pymilvus import Collection, MilvusException

logger = logging.getLogger(__name__)


class DataIndexingService:
    def __init__(self, org_id: str):
        self.org_id = org_id
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
        logger.info("Storing vectors & index. org_id=%s", self.org_id)

        vector_index = VectorStoreIndex(
            nodes=nodes, storage_context=self.storage_context
        )

        logger.info(
            "Stored index to vector store. org_id=%s, index_id=%s",
            self.org_id,
            vector_index.index_id,
        )

    def add_nodes(self, nodes: list[NodeWithEmbedding]) -> None:
        logger.info(
            "Adding nodes. org_id=%s, nodes=%s",
            self.org_id,
            nodes,
        )

        try:
            self.storage_context.vector_store.add(nodes)
        except MilvusException as e:
            logger.error(
                "org_id=%s, nodes=%s, error=%s",
                self.org_id,
                nodes,
                e,
            )

        logger.info(
            "Finished adding nodes. org_id=%s, nodes=%s",
            self.org_id,
            nodes,
        )

    def delete_nodes(self, ref_doc_ids: list[str]) -> None:
        logger.info(
            "Deleting nodes. org_id=%s, ref_doc_ids=%s",
            self.org_id,
            ref_doc_ids,
        )

        for ref_doc_id in ref_doc_ids:
            try:
                self.storage_context.vector_store.delete(ref_doc_id=ref_doc_id)
            except MilvusException as e:
                logger.error(
                    "org_id=%s, ref_doc_id=%s, error=%s",
                    self.org_id,
                    ref_doc_id,
                    e,
                )

        logger.info(
            "Finished deleting nodes. org_id=%s, ref_doc_ids=%s",
            self.org_id,
            ref_doc_ids,
        )

    def drop_collection(self) -> None:
        logger.info(
            "Dropping collection. org_id=%s",
            self.org_id,
        )

        try:
            collection: Collection = self.storage_context.vector_store.collection
            collection.drop()
        except MilvusException as e:
            logger.error(
                "org_id=%s, error=%s",
                self.org_id,
                e,
            )

        logger.info(
            "Finished dropping collection. org_id=%s",
            self.org_id,
        )

    def load_vector_index(self) -> VectorStoreIndex:
        logger.info(
            "Loading vector index. org_id=%s",
            self.org_id,
        )

        return load_index_from_storage(storage_context=self.storage_context)

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
