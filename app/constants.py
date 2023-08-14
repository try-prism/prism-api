"""Set of constants."""
import os

import openai
from dotenv import load_dotenv
from ray.runtime_env import RuntimeEnv

load_dotenv()

# Current Environment
PRISM_ENV = os.environ["PRISM_ENV"]


# Secrets
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_ORG_KEY = os.environ["OPENAI_ORG_KEY"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
MERGE_API_KEY = os.environ["MERGE_API_KEY"]
COHERE_API_KEY = os.environ["COHERE_API_KEY"]

# Need to set this to not get RetryError for now
openai.api_key = os.getenv("OPENAI_API_KEY")


# Model
DEFAULT_OPENAI_MODEL = os.environ["DEFAULT_OPENAI_MODEL"]


# DynamoDB Tables
DYNAMODB_USER_TABLE = os.environ["DYNAMODB_USER_TABLE"]
DYNAMODB_FILE_TABLE = os.environ["DYNAMODB_FILE_TABLE"]
DYNAMODB_ORGANIZATION_TABLE = os.environ["DYNAMODB_ORGANIZATION_TABLE"]
DYNAMODB_WHITELIST_TABLE = os.environ["DYNAMODB_WHITELIST_TABLE"]


# DynamoDB Indexes
DYNAMODB_FILE_TABLE_INDEX = os.environ["DYNAMODB_FILE_TABLE_INDEX"]


# SES Configurations
SES_SENDER_EMAIL = "noreply@tryprism.ai"
DEFAULT_SIGNUP_URL = "http://tryprism.ai/signup?user="


# Cognito Configurations
COGNITO_USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]


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
RAY_ADDRESS = os.environ["RAY_ADDRESS"]
RAY_RUNTIME_ENV = RuntimeEnv(
    pip=["llama_index", "langchain", "mergepythonclient", "nltk", "unstructured"],
    env_vars={"MERGE_API_KEY": MERGE_API_KEY},
)
