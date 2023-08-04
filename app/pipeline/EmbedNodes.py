from typing import Dict, List

from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from llama_index.data_structs import Node


class EmbedNodes:
    """https://huggingface.co/spaces/mteb/leaderboard"""

    def __init__(self):
        """
        Use GPU for embedding and specify a large enough batch size to maximize GPU utilization.
        Remove the "device": "cuda" to use CPU instead.
        """
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/gte-large",
            model_kwargs={"device": "cuda"},
            encode_kwargs={"device": "cuda", "batch_size": 100},
        )

    def __call__(self, node_batch: Dict[str, List[Node]]) -> Dict[str, List[Node]]:
        nodes = node_batch["node"]
        text = [node.text for node in nodes]
        embeddings = self.embedding_model.embed_documents(text)

        assert len(nodes) == len(embeddings)

        for node, embedding in zip(nodes, embeddings):
            node.embedding = embedding

        return {"embedded_nodes": nodes}
