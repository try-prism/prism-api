import datetime
from collections.abc import Sequence
from typing import IO

from exceptions import PrismDBException, PrismException
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from llama_index import Document
from llama_index.node_parser import SimpleNodeParser
from llama_index.schema import BaseNode, TextNode
from loguru import logger
from merge.resources.filestorage.types import File
from storage import DynamoDBService, MergeService

from .CustomUnstructuredReader import CustomUnstructuredReader


class DataPipelineServiceLocal:
    def __init__(self, org_id: str, account_token: str):
        self.org_id = org_id
        self.account_token = account_token
        self.loader = CustomUnstructuredReader()
        self.parser = SimpleNodeParser()
        self.dynamodb_service = DynamoDBService()
        self.merge_service = MergeService(account_token=account_token)
        today = datetime.date.today()
        self.process_date = str(
            datetime.datetime(today.year, today.month, today.day).timestamp()
        )
        self.not_processed_file_ids: list[str] = []

    def get_embedded_nodes(self, all_files: list[File]) -> Sequence[BaseNode]:
        logger.info(
            "org_id={}, account_token={}",
            self.org_id,
            self.account_token,
        )

        loaded_docs = self.load_data(all_files)

        # remove not processed files from the database and organization
        try:
            self.dynamodb_service.modify_organization_files(
                org_id=self.org_id, file_ids=self.not_processed_file_ids, is_remove=True
            )
            self.dynamodb_service.modify_file_in_batch(
                file_ids=self.not_processed_file_ids, is_remove=True
            )
        except PrismDBException as e:
            logger.error(
                "org_id={}, account_token={}, error={}",
                self.org_id,
                self.account_token,
                e,
            )

        nodes = self.generate_nodes(loaded_docs)
        embeddings = self.generate_embeddings(nodes)

        return embeddings

    def load_and_parse_files(
        self, file_row: dict[str, File]
    ) -> list[dict[str, Document]]:
        logger.info(
            "Started loading and parsing files. account_token={}", self.account_token
        )
        documents = []

        try:
            file_in_bytes: IO[bytes] = self.merge_service.download_file(
                file=file_row["data"], in_bytes=True
            )
            loaded_doc = self.loader.load_data(
                file=file_in_bytes, split_documents=False
            )
            loaded_doc[0].doc_id = file_row["data"].id
            loaded_doc[0].metadata = {
                "file_id": file_row["data"].id,
                "process_date": self.process_date,
            }

            documents.extend(loaded_doc)
        except PrismException as e:
            logger.error("file_row={}, error={}", file_row, e)
            self.not_processed_file_ids.append(file_row["data"].id)

        return [{"doc": doc} for doc in documents]

    def load_data(self, all_files: list[File]) -> list:
        logger.info("Started loading data. account_token={}", self.account_token)

        # Get the file data from all files & Create the Ray Dataset pipeline
        all_items = [{"data": file} for file in all_files]
        all_file_ids = [file.id for file in all_files]

        try:
            self.dynamodb_service.modify_organization_files(
                org_id=self.org_id, file_ids=all_file_ids, is_remove=False
            )
            self.dynamodb_service.modify_file_in_batch(
                account_token=self.account_token, files=all_files, is_remove=False
            )
        except PrismDBException as e:
            logger.error(
                "org_id={}, account_token={}, error={}",
                self.org_id,
                self.account_token,
                e,
            )

        loaded_docs = []
        for file in all_items:
            file_docs = self.load_and_parse_files(file)
            loaded_docs.extend(file_docs)

        logger.info("Finished loading data. account_token=", self.account_token)

        return loaded_docs

    def convert_documents_into_nodes(
        self, documents: dict[str, Document]
    ) -> list[dict[str, TextNode]]:
        logger.info(
            "Started converting documents into nodes. account_token={}",
            self.account_token,
        )
        # Convert the loaded documents into llama_index Nodes.
        # This will split the documents into chunks.

        document = documents["doc"]
        nodes = self.parser.get_nodes_from_documents([document])

        return [{"node": node} for node in nodes]

    def generate_nodes(self, loaded_docs) -> list:
        logger.info("Started generating nodes. account_token={}", self.account_token)

        nodes = []

        for doc in loaded_docs:
            res = self.convert_documents_into_nodes(doc)
            nodes.extend(res)

        logger.info("Finished generating nodes. account_token={}", self.account_token)

        return nodes

    def generate_embeddings(self, nodes) -> Sequence[BaseNode]:
        logger.info(
            "Started generating embeddings. account_token={}", self.account_token
        )

        embeddings = []
        embedding_model = HuggingFaceEmbeddings(model_name="thenlper/gte-base")

        for nod in nodes:
            nodes = nod["node"]
            text = [node.text for node in nodes]
            embeddings = embedding_model.embed_documents(text)

            assert len(nodes) == len(embeddings)

            for node, embedding in zip(nodes, embeddings):
                node.embedding = embedding

            embedding.append({"embedded_nodes": nodes})

        logger.info(
            "Finished generating embeddings. account_token={}", self.account_token
        )

        return embeddings
