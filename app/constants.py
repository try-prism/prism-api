"""Set of constants."""
import os

from dotenv import load_dotenv

load_dotenv()

# Secrets
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_ORG_KEY = os.environ["OPENAI_ORG_KEY"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
MERGE_API_KEY = os.environ["MERGE_API_KEY"]


# DynamoDB Tables
DYNAMODB_USER_TABLE = os.environ["DYNAMODB_USER_TABLE"]
DYNAMODB_FILE_TABLE = os.environ["DYNAMODB_FILE_TABLE"]
DYNAMODB_ORGANIZATION_TABLE = os.environ["DYNAMODB_ORGANIZATION_TABLE"]
DYNAMODB_STORAGE_CONTEXT_TABLE = os.environ["DYNAMODB_STORAGE_CONTEXT_TABLE"]
DYNAMODB_WHITELIST_TABLE = os.environ["DYNAMODB_WHITELIST_TABLE"]


# S3 Buckets
S3_FILE_BUCKET = os.environ["S3_FILE_BUCKET"]


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
