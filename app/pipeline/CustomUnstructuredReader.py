"""
Custom Unstructured file reader for Prism AI
https://github.com/emptycrown/llama-hub

Original Implementation: llama_hub/file/unstructured/base.py

A parser for unstructured text files using Unstructured.io.
Supports .html, .rtf, .txt, .csv, .doc, .docx, .pdf, .ppt, .pptx, and .xlsx documents.
"""
import re
from typing import IO, Any

from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document


class CustomUnstructuredReader(BaseReader):
    """Custom unstructured text reader for a variety of files."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init params."""
        super().__init__(*args, **kwargs)
        self.clean_regex = re.compile(r"[\t\n]")
        self.compress_regex = re.compile(r" +")

        # Prerequisite for Unstructured.io to work
        import nltk

        nltk.download("punkt")
        nltk.download("averaged_perceptron_tagger")

    def load_data(
        self,
        file: IO[bytes],
        extra_info: dict | None = None,
        split_documents: bool | None = False,
    ) -> list[Document]:
        """Parse file."""
        from unstructured.partition.auto import partition

        elements = partition(file=file)
        text_chunks = [" ".join(str(el).split()) for el in elements]

        if split_documents:
            return [
                Document(text=chunk, extra_info=extra_info or {})
                for chunk in text_chunks
            ]
        else:
            clean_text = self.clean_regex.sub(" ", "\n".join(text_chunks))
            clean_text = self.compress_regex.sub(" ", clean_text)
            return [Document(text=clean_text, extra_info=extra_info or {})]
