"""Set of constants."""
import os

from dotenv import load_dotenv
from ray.runtime_env import RuntimeEnv

load_dotenv()

# Secrets
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_ORG_KEY = os.environ["OPENAI_ORG_KEY"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
MERGE_API_KEY = os.environ["MERGE_API_KEY"]


# Model
DEFAULT_OPENAI_MODEL = os.environ["DEFAULT_OPENAI_MODEL"]


# DynamoDB Tables
DYNAMODB_USER_TABLE = os.environ["DYNAMODB_USER_TABLE"]
DYNAMODB_FILE_TABLE = os.environ["DYNAMODB_FILE_TABLE"]
DYNAMODB_ORGANIZATION_TABLE = os.environ["DYNAMODB_ORGANIZATION_TABLE"]
DYNAMODB_STORAGE_CONTEXT_TABLE = os.environ["DYNAMODB_STORAGE_CONTEXT_TABLE"]
DYNAMODB_WHITELIST_TABLE = os.environ["DYNAMODB_WHITELIST_TABLE"]


# S3 Buckets
S3_FILE_BUCKET = os.environ["S3_FILE_BUCKET"]


# Zilliz Cloud
ZILLIZ_CLOUD_HOST = os.environ["ZILLIZ_CLOUD_HOST"]
ZILLIZ_CLOUD_PORT = os.environ["ZILLIZ_CLOUD_PORT"]
ZILLIZ_CLOUD_USER = os.environ["ZILLIZ_CLOUD_USER"]
ZILLIZ_CLOUD_PASSWORD = os.environ["ZILLIZ_CLOUD_PASSWORD"]


# File Processing Properties
SUPPORTED_EXTENSIONS = [
    "html",
    "rtf",
    "txt",
    "csv",
    "doc",
    "docx",
    "pdf",
    "ppt",
    "pptx",
    "xlsx",
]

# https://docs.ray.io/en/latest/ray-core/api/doc/ray.runtime_env.RuntimeEnv.html
RAY_RUNTIME_ENV = RuntimeEnv(
    pip=["llama_index", "langchain", "mergepythonclient", "nltk", "unstructured"],
    env_vars={"MERGE_API_KEY": MERGE_API_KEY},
)
