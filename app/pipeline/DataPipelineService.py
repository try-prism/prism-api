import logging
from collections.abc import Sequence
from typing import IO

import ray
from constants import RAY_RUNTIME_ENV
from exceptions import PrismMergeException
from llama_index import Document
from llama_index.node_parser import SimpleNodeParser
from llama_index.schema import BaseNode, TextNode
from merge.resources.filestorage.types import File
from ray.data import ActorPoolStrategy, Dataset, from_items
from ray.data.dataset import MaterializedDataset
from storage import MergeService

from .CustomUnstructuredReader import CustomUnstructuredReader
from .EmbedNodes import EmbedNodes

logger = logging.getLogger(__name__)

ray.init(runtime_env=RAY_RUNTIME_ENV)


class DataPipelineService:
    def __init__(self, account_token: str):
        self.account_token = account_token
        self.loader = CustomUnstructuredReader()
        self.parser = SimpleNodeParser()
        self.merge_service = MergeService(account_token=account_token)

    def get_embedded_nodes(self, all_files: list[File]) -> Sequence[BaseNode]:
        loaded_docs = self.load_data(all_files)
        nodes = self.generate_nodes(loaded_docs)
        ray_docs_nodes = self.generate_embeddings(nodes)

        return ray_docs_nodes

    def load_and_parse_files(
        self, file_row: dict[str, File]
    ) -> list[dict[str, Document]]:
        documents = []

        try:
            file_in_bytes: IO[bytes] = self.merge_service.download_file(
                file=file_row["data"], in_bytes=True
            )
        except PrismMergeException as e:
            logger.error("file_row=%s, error=%s", file_row, e)

        loaded_doc = self.loader.load_data(file=file_in_bytes, split_documents=False)
        loaded_doc[0].extra_info = {"file_id": file_row["data"].id}
        documents.extend(loaded_doc)

        return [{"doc": doc} for doc in documents]

    def load_data(self, all_files: list[File]) -> Dataset:
        logger.info("Started loading data. account_token=%s", self.account_token)

        # Get the file data from all files & Create the Ray Dataset pipeline
        all_items = [{"data": file} for file in all_files]
        ds: MaterializedDataset = from_items(all_items)

        # Use `flat_map` since there is a 1:N relationship.
        # Each filepath returns multiple documents.
        loaded_docs = ds.flat_map(self.load_and_parse_files)
        logger.info("Finished loading data. account_token=", self.account_token)

        return loaded_docs

    def convert_documents_into_nodes(
        self, documents: dict[str, Document]
    ) -> list[dict[str, TextNode]]:
        # Convert the loaded documents into llama_index Nodes.
        # This will split the documents into chunks.

        document = documents["doc"]
        nodes = self.parser.get_nodes_from_documents([document])

        return [{"node": node} for node in nodes]

    def generate_nodes(self, loaded_docs: Dataset) -> Dataset:
        logger.info("Started generating nodes. account_token=%s", self.account_token)

        # Use `flat_map` since there is a 1:N relationship. Each document returns multiple nodes.
        nodes = loaded_docs.flat_map(self.convert_documents_into_nodes)
        logger.info("Finished generating nodes. account_token=%s", self.account_token)

        return nodes

    def generate_embeddings(self, nodes: Dataset) -> Sequence[BaseNode]:
        """
        Use `map_batches` to specify a batch size to maximize GPU utilization.
        We define `EmbedNodes` as a class instead of a function
        so we only initialize the embedding model once.
        """

        # This state can be reused for multiple batches.
        embedded_nodes = nodes.map_batches(
            EmbedNodes,
            batch_size=100,
            # Use 1 GPU per actor.
            num_gpus=1,
            # There are 4 GPUs in the cluster. Each actor uses 1 GPU. So we want 4 total actors.
            compute=ActorPoolStrategy(size=4),
        )

        # Trigger execution and collect all the embedded nodes.
        ray_docs_nodes = []

        for row in embedded_nodes.iter_rows():
            node = row["embedded_nodes"]
            assert node.embedding is not None
            ray_docs_nodes.append(node)

        return ray_docs_nodes
